    // Weather background styles
const weatherStyles = {
    default: {
        background: 'linear-gradient(to bottom, #1a365d, #2d3748)',
    },
    Clear: {
        background: 'linear-gradient(135deg, #FF6B6B, #FFB88C)',
    },
    Clouds: {
        background: 'linear-gradient(135deg, #4B6CB7, #182848)',
    },
    Rain: {
        background: 'linear-gradient(135deg, #3E5151, #DECBA4)',
    },
    Snow: {
        background: 'linear-gradient(135deg, #E6DADA, #274046)',
    },
    Thunderstorm: {
        background: 'linear-gradient(135deg, #373B44, #4286f4)',
    },
    Mist: {
        background: 'linear-gradient(135deg, #606c88, #3f4c6b)',
    }
};

let cachedData = {};
let currentRequest = null;
let forecastChart = null;
let searchTimeout = null;

let sunsetTime = null;
let formattedTime = null;

function showLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
    }
}

function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 500);
    }
}

async function searchLocation() {
    const locationInput = document.getElementById('locationInput');
    const location = locationInput?.value?.trim();
    
    if (!location) {
        showError('Please enter a location');
        return;
    }

    // Validate location format
    if (!location.includes(',')) {
        showError('Please enter location as "City, State" (e.g. "Boston, MA")');
        return;
    }

    const [city, state] = location.split(',').map(part => part.trim());
    if (!city || !state || state.length !== 2) {
        showError('Please enter a valid city and 2-letter state code (e.g. "Boston, MA")');
        return;
    }

    // Check cache first
    const cacheKey = `${location}-1`;
    if (cachedData[cacheKey]) {
        displayResults(cachedData[cacheKey]);
        return;
    }

    showLoading();
    clearError();
    
    try {
        // Cancel any existing request
        if (currentRequest) {
            currentRequest.abort();
        }

        // Create a new AbortController
        const controller = new AbortController();
        currentRequest = controller;

        console.log('Sending request:', { location, days: 1 });
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                location: location,
                days: 1 
            }),
            signal: controller.signal
        });

        const responseText = await response.text();
        console.log('Response text:', responseText);
        
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            console.error('Error parsing JSON:', e, 'Response text:', responseText);
            throw new Error('Invalid response from server. Please try again.');
        }

        if (!response.ok) {
            console.error('Server error:', data);
            throw new Error(data.error || `Server error: ${response.status}`);
        }

        if (data.error) {
            console.error('API error:', data.error);
            throw new Error(data.error);
        }

        if (!data.predictions || !Array.isArray(data.predictions)) {
            console.error('Invalid predictions data:', data);
            throw new Error('Invalid forecast data received');
        }

        if (data.predictions.length === 0) {
            console.error('No predictions received');
            throw new Error('No forecast data available for this location');
        }

        if (data.predictions.length !== 1) {
            console.error(`Received ${data.predictions.length} predictions for 1 day request`);
            throw new Error('Incomplete forecast data received');
        }

        // Cache the successful response
        cachedData[cacheKey] = data;
        
        // Update the display based on the number of days
        displayResults(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'An error occurred while fetching the prediction');
    } finally {
        hideLoading();
        currentRequest = null;
    }
}

function showError(message) {
    const container = document.querySelector('.max-w-4xl.mx-auto.mb-8');
    if (!container) return;

    // Create or get error message element
    let errorElement = document.getElementById('errorMessage');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.id = 'errorMessage';
        errorElement.className = 'glass-card max-w-4xl mx-auto p-4 mb-6 bg-red-500 bg-opacity-20 text-white text-center';
        container.insertAdjacentElement('afterend', errorElement);
    }
    
    errorElement.textContent = message;
    errorElement.style.display = 'block';
    
    // Hide after 5 seconds
    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 5000);
}

function clearError() {
    const errorElement = document.getElementById('errorMessage');
    if (errorElement) {
        errorElement.style.display = 'none';
    }
}

function displayResults(data) {
    const sunsetPrediction = document.getElementById('sunsetPrediction');
    const prediction = data.predictions[0];
    
    console.log('Received prediction data:', prediction);
    console.log('Sunset time from API:', prediction.sunset_time);
    
    // Calculate quality score color
    const qualityScore = prediction.quality_score;
    let qualityColor;
    if (qualityScore >= 8) {
        qualityColor = '#22c55e'; // green
    } else if (qualityScore >= 6) {
        qualityColor = '#eab308'; // yellow
    } else {
        qualityColor = '#ef4444'; // red
    }

    // Parse and format sunset time
    const sunsetTime = new Date(prediction.sunset_time);
    console.log('Parsed sunset time:', sunsetTime);
    
    if (isNaN(sunsetTime.getTime())) {
        console.error('Invalid sunset time received:', prediction.sunset_time);
        showError('Error: Invalid sunset time received from server');
        return;
    }
    
    // Calculate arrival time (30 minutes before sunset)
    const arrivalTime = new Date(sunsetTime.getTime() - (30 * 60 * 1000));
    
    // Format times for display
    const timeFormatOptions = { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true
    };
    
    const formattedSunsetTime = sunsetTime.toLocaleTimeString('en-US', timeFormatOptions);
    const formattedArrivalTime = arrivalTime.toLocaleTimeString('en-US', timeFormatOptions);

    // Update background based on time of day and weather
    document.body.style.background = weatherStyles[prediction.weather_condition]?.background || weatherStyles.default.background;

    // Show the prediction container
    sunsetPrediction.classList.remove('hidden');
    
    // Update prediction content
    const singleDayView = document.getElementById('singleDayView');
    singleDayView.innerHTML = `
        <div class="text-center mb-8">
            <h2 class="text-3xl font-bold text-white mb-2">${data.location}</h2>
            <p class="text-lg text-gray-300">${prediction.date}</p>
        </div>
        
        <div class="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
            <div class="sunset-stat">
                <i class="fas fa-sun text-4xl text-yellow-400 mb-2"></i>
                <p class="text-sm text-gray-300">Sunset Time</p>
                <p class="text-xl font-bold text-white">${formattedSunsetTime}</p>
                <p class="text-sm text-gray-300 mt-1">Arrive by ${formattedArrivalTime}</p>
            </div>
            
            <div class="sunset-stat">
                <div class="relative quality-circle-container">
                    <svg class="quality-circle" viewBox="0 0 36 36">
                        <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" 
                              fill="none" 
                              stroke="rgba(255, 255, 255, 0.2)" 
                              stroke-width="2"/>
                        <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" 
                              fill="none" 
                              stroke="${qualityColor}" 
                              stroke-width="2"
                              style="stroke-dasharray: 100; stroke-dashoffset: ${100 - (qualityScore * 10)}"/>
                    </svg>
                    <div class="absolute inset-0 flex flex-col items-center justify-center">
                        <p class="text-sm text-gray-300">Quality</p>
                        <p class="text-xl font-bold text-white">${qualityScore}/10</p>
                    </div>
                </div>
            </div>
            
            <div class="sunset-stat">
                <i class="fas fa-cloud text-4xl text-blue-400 mb-2"></i>
                <p class="text-sm text-gray-300">Cloud Cover</p>
                <p class="text-xl font-bold text-white">${prediction.clouds}%</p>
            </div>
            
            <div class="sunset-stat">
                <i class="fas fa-wind text-4xl text-gray-400 mb-2"></i>
                <p class="text-sm text-gray-300">Wind Speed</p>
                <p class="text-xl font-bold text-white">${prediction.wind_speed} m/s</p>
            </div>
        </div>

        <div class="glass-card p-6">
            <div class="flex items-center gap-2 mb-4">
                <i class="fas fa-camera text-2xl text-yellow-400"></i>
                <h4 class="text-xl font-bold text-white">Photography Tips</h4>
            </div>
            <div class="space-y-4">
                <p class="text-lg text-white">${getPhotographyTip(prediction)}</p>
                <p class="text-sm text-gray-300">
                    For the best experience, arrive by ${formattedArrivalTime} to set up your equipment and find the perfect composition. Sunset will occur at ${formattedSunsetTime}.
                </p>
            </div>
        </div>
    `;

    // Smooth scroll to results
    sunsetPrediction.scrollIntoView({ behavior: 'smooth' });
}

function getPhotographyTip(prediction) {
    const conditions = [];
    
    if (prediction.clouds <= 30) {
        conditions.push("Clear skies suggest vibrant colors. Look for interesting foreground elements to add depth to your composition.");
    } else if (prediction.clouds <= 70) {
        conditions.push("Partial cloud cover can create dramatic light rays and colorful cloud formations.");
    } else {
        conditions.push("Heavy cloud cover may diffuse the light. Focus on moody compositions and silhouettes.");
    }

    if (prediction.wind_speed <= 3) {
        conditions.push("Low wind speeds are perfect for long exposures and reflections.");
    } else if (prediction.wind_speed <= 7) {
        conditions.push("Moderate wind might create interesting cloud movements.");
    } else {
        conditions.push("High winds may cause camera shake. Use a sturdy tripod and faster shutter speeds.");
    }

    return conditions.join(' ');
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    const locationInput = document.getElementById('locationInput');
    const todayBtn = document.getElementById('todayBtn');

    // Search on enter key
    locationInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchLocation();
        }
    });

    // Search on button click
    todayBtn.addEventListener('click', searchLocation);
});
