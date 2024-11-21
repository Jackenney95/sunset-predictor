# Sunset Predictor

A web application that helps you find the perfect spot and time for watching sunsets. It analyzes various factors including weather conditions, cloud cover, and timing to provide a quality score for sunset viewing.

## Features

- Sunset time prediction for any location
- Weather condition analysis
- Quality score calculation based on multiple factors
- Photography tips based on conditions
- Responsive design
- Dynamic backgrounds based on weather

## Local Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the root directory with your API keys:
   ```
   OPENWEATHER_API_KEY=your_openweather_api_key
   FLASK_SECRET_KEY=your_secret_key
   ```

## Running Locally

```bash
python app.py
```

The application will be available at `http://localhost:5003`

## Deployment to Render

1. Create a new account on [Render](https://render.com) if you don't have one
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository or use the public URL
4. Fill in the following settings:
   - Name: sunset-predictor (or your preferred name)
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Add the following environment variables:
   - `OPENWEATHER_API_KEY`: Your OpenWeather API key
   - `FLASK_SECRET_KEY`: A random string for session security
6. Click "Create Web Service"

Your app will be deployed and available at a URL like: `https://your-app-name.onrender.com`

## How it Works

The application combines several factors to predict sunset quality:
- Cloud cover (optimal around 50% for spectacular colors)
- Humidity levels
- Wind conditions
- Precise sunset timing

## API Requirements

You'll need to obtain an API key from:
1. OpenWeatherMap (https://openweathermap.org/api)
   - Sign up for a free account
   - Go to "My API Keys"
   - Copy your API key
