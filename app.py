from flask import Flask, jsonify, request, render_template
from datetime import datetime, timedelta
import requests
import os
import logging
from dotenv import load_dotenv
import json
from geopy.geocoders import Nominatim
from suntime import Sun
import numpy as np
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask_cors import CORS
import pytz
from timezonefinder import TimezoneFinder

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# Set up logging with more detail
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_location_coords(location_name):
    print(f"\n--- Getting coordinates for: {location_name} ---")  # Debug print
    geolocator = Nominatim(user_agent="sunset_predictor")
    try:
        location = geolocator.geocode(location_name)
        if location:
            print(f"Found location: {location.address}")  # Debug print
            print(f"Coordinates: {location.latitude}, {location.longitude}")  # Debug print
            return location.latitude, location.longitude, location.address
        print("Location not found by geocoder")  # Debug print
        return None, None, None
    except Exception as e:
        print(f"Error in geocoding: {str(e)}")  # Debug print
        return None, None, None

def get_weather_data(lat, lon, days=1):
    """Get weather data from OpenWeatherMap API."""
    if not OPENWEATHER_API_KEY:
        logger.error("OpenWeather API key is not set")
        raise Exception("Weather service configuration error. Please check API key.")

    try:
        if days == 1:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        else:
            # Use the One Call API for multi-day forecasts
            url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,alerts&appid={OPENWEATHER_API_KEY}&units=metric"
            
        logger.debug(f"Making request to OpenWeatherMap API: {url.replace(OPENWEATHER_API_KEY, 'HIDDEN_KEY')}")
        
        response = requests.get(url, timeout=10)
        logger.debug(f"Response status code: {response.status_code}")
        
        if response.status_code == 401:
            logger.error("API key authentication failed")
            raise Exception("Weather service authentication failed. Please check API key.")
        elif response.status_code == 429:
            logger.error("API rate limit exceeded")
            raise Exception("Weather service rate limit exceeded. Please try again later.")
        elif response.status_code != 200:
            logger.error(f"OpenWeatherMap API error: {response.status_code} - {response.text}")
            raise Exception(f"Weather service error: {response.text}")
            
        data = response.json()
        logger.debug(f"Weather data received: {json.dumps(data, indent=2)}")
        
        # For multi-day forecasts, validate and process the data
        if days > 1:
            if 'daily' not in data:
                logger.error("Invalid forecast data structure - missing 'daily' data")
                raise Exception("Invalid forecast data received from weather service")
                
            daily_forecasts = data['daily'][:days]  # Get only the requested number of days
            if not daily_forecasts:
                logger.error("Empty forecast list received")
                raise Exception("No forecast data available")
                
            # Convert One Call API format to match our expected format
            processed_data = {
                'list': []
            }
            
            for daily in daily_forecasts:
                forecast_entry = {
                    'dt': daily['dt'],
                    'main': {
                        'temp': daily['temp']['day']
                    },
                    'weather': [
                        {
                            'main': daily['weather'][0]['main'],
                            'description': daily['weather'][0]['description']
                        }
                    ],
                    'clouds': {
                        'all': daily.get('clouds', 0)
                    },
                    'wind': {
                        'speed': daily.get('wind_speed', 0)
                    }
                }
                processed_data['list'].append(forecast_entry)
            
            return processed_data
            
        return data
        
    except requests.exceptions.Timeout:
        logger.error("Weather API request timed out")
        raise Exception("Weather service is taking too long to respond. Please try again.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Weather API request error: {str(e)}")
        raise Exception("Unable to fetch weather data. Please try again later.")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse weather API response: {str(e)}")
        raise Exception("Invalid response from weather service. Please try again later.")

def calculate_quality_score(weather_data):
    """Calculate sunset quality score based on weather conditions."""
    try:
        base_score = 10
        deductions = 0
        
        # Extract weather data based on API response structure
        if 'weather' in weather_data and 'main' in weather_data['weather'][0]:
            weather_condition = weather_data['weather'][0]['main'].lower()
            logger.debug(f"Weather condition: {weather_condition}")
        else:
            logger.error("Missing weather condition in data")
            return 5  # Return average score if weather data is missing
        
        # Cloud cover impact (0-10 points)
        clouds = weather_data.get('clouds', {}).get('all', 0)
        logger.debug(f"Cloud coverage: {clouds}%")
        if clouds > 80:
            deductions += 4
        elif clouds > 60:
            deductions += 3
        elif clouds > 40:
            deductions += 2
        elif clouds > 20:
            deductions += 1
        
        # Wind speed impact (0-3 points)
        wind_speed = weather_data.get('wind', {}).get('speed', 0)
        logger.debug(f"Wind speed: {wind_speed} m/s")
        if wind_speed > 10:
            deductions += 3
        elif wind_speed > 7:
            deductions += 2
        elif wind_speed > 5:
            deductions += 1
        
        # Weather condition impact
        if 'rain' in weather_condition or 'snow' in weather_condition:
            deductions += 5
        elif 'thunderstorm' in weather_condition:
            deductions += 7
        elif 'drizzle' in weather_condition:
            deductions += 3
        elif 'mist' in weather_condition or 'fog' in weather_condition:
            deductions += 2
        
        # Calculate final score
        final_score = max(0, base_score - deductions)
        logger.debug(f"Final quality score: {final_score} (Base: {base_score}, Deductions: {deductions})")
        
        return final_score
        
    except Exception as e:
        logger.error(f"Error calculating quality score: {str(e)}")
        logger.error(f"Weather data causing error: {json.dumps(weather_data, indent=2)}")
        return 5  # Return average score in case of error

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        logger.info(f"Received request data: {data}")
        
        if not data:
            logger.error("No JSON data received in request")
            return jsonify({'error': 'No data provided'}), 400
            
        if 'location' not in data:
            logger.error("No location provided in request data")
            return jsonify({'error': 'Location is required'}), 400
            
        location = data['location']
        logger.info(f"Processing location: {location}")
        
        # Get coordinates
        try:
            geolocator = Nominatim(user_agent="sunset_predictor")
            location_data = geolocator.geocode(location, timeout=10)
            
            if not location_data:
                logger.error(f"Location not found: {location}")
                return jsonify({'error': 'Location not found. Please try a different location.'}), 404
                
            logger.info(f"Found coordinates for {location}: {location_data.latitude}, {location_data.longitude}")
            
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}")
            return jsonify({'error': 'Unable to find location. Please check the address and try again.'}), 404
            
        lat, lon = location_data.latitude, location_data.longitude
        logger.info(f"Using coordinates: lat={lat}, lon={lon}")
        
        # Get timezone for the location
        try:
            tf = TimezoneFinder()
            timezone_str = tf.timezone_at(lat=lat, lng=lon)
            if timezone_str is None:
                logger.warning("Timezone not found, using UTC")
                timezone_str = 'UTC'
            timezone = pytz.timezone(timezone_str)
            logger.info(f"Using timezone: {timezone_str}")
        except Exception as e:
            logger.error(f"Timezone error: {str(e)}")
            timezone_str = 'UTC'
            timezone = pytz.UTC
        
        # Get weather data
        try:
            weather_data = get_weather_data(lat, lon, days=1)
            if not weather_data:
                logger.error("No weather data returned from API")
                return jsonify({'error': 'Weather data not available'}), 503
            logger.info(f"Weather data received: {json.dumps(weather_data, indent=2)}")
                
        except Exception as e:
            logger.error(f"Error fetching weather data: {str(e)}")
            return jsonify({'error': str(e)}), 503
            
        # Calculate sunset time and prediction
        try:
            sun = Sun(lat, lon)
            current_date = datetime.now(timezone)
            logger.info(f"Calculating sunset for date: {current_date}")
            
            sunset_time = sun.get_sunset_time(current_date)
            logger.info(f"Raw sunset time: {sunset_time}")
            
            # Convert UTC sunset time to local timezone
            if sunset_time.tzinfo is None or sunset_time.tzinfo.utcoffset(sunset_time) is None:
                sunset_time = pytz.utc.localize(sunset_time)
            sunset_time = sunset_time.astimezone(timezone)
            logger.info(f"Localized sunset time: {sunset_time}")
            
            quality_score = calculate_quality_score(weather_data)
            logger.info(f"Quality score calculated: {quality_score}")
            
            prediction = {
                'date': current_date.strftime('%Y-%m-%d'),
                'sunset_time': sunset_time.isoformat(),  # Use ISO format for better JavaScript compatibility
                'weather_condition': weather_data['weather'][0]['main'],
                'quality_score': quality_score,
                'clouds': weather_data['clouds']['all'],
                'wind_speed': weather_data['wind']['speed'],
                'temperature': round(weather_data['main']['temp'])
            }
            logger.info(f"Final prediction data: {json.dumps(prediction, indent=2)}")
            
            response_data = {
                'location': location_data.address,
                'predictions': [prediction]
            }
            
            logger.info("Successfully generated prediction")
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Error generating prediction: {str(e)}")
            logger.exception("Full traceback:")
            return jsonify({'error': f'Error calculating sunset time: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in predict route: {str(e)}")
        logger.exception("Full traceback:")
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@app.route('/reverse-geocode')
def reverse_geocode():
    try:
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        
        if not lat or not lon:
            return jsonify({'error': 'Latitude and longitude are required'}), 400
            
        geolocator = Nominatim(user_agent="sunset_predictor")
        location = geolocator.reverse((lat, lon))
        
        if not location:
            return jsonify({'error': 'Location not found'}), 404
            
        return jsonify({
            'location': location.address,
            'lat': float(lat),
            'lon': float(lon)
        })
        
    except Exception as e:
        logger.error(f"Error in reverse_geocode: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_photo():
    try:
        if 'photo' not in request.files:
            return jsonify({'error': 'No photo uploaded'}), 400
            
        photo = request.files['photo']
        location = request.form.get('location')
        date = request.form.get('date')
        
        if not photo or not location or not date:
            return jsonify({'error': 'Missing required fields'}), 400
            
        if photo.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if photo and allowed_file(photo.filename):
            # Create uploads directory if it doesn't exist
            uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Save the file with a secure filename
            filename = secure_filename(f"{date}_{location}_{photo.filename}")
            photo.save(os.path.join(uploads_dir, filename))
            
            # Here you would typically save the photo metadata to a database
            # For now, we'll just return success
            return jsonify({
                'success': True,
                'message': 'Photo uploaded successfully',
                'filename': filename
            })
            
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        logger.error(f"Error in upload_photo: {str(e)}")
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/favorites', methods=['GET'])
def get_favorites():
    # Mock favorites data
    favorites = [
        {
            'location': 'Malibu Beach',
            'latitude': 34.0259,
            'longitude': -118.7798
        },
        {
            'location': 'Grand Canyon',
            'latitude': 36.0544,
            'longitude': -112.1401
        }
    ]
    return jsonify(favorites)

if __name__ == '__main__':
    print("Starting Flask application...")
    app.run(debug=True, port=5003, host='127.0.0.1')  # Changed to localhost
