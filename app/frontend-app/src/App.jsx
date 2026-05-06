import { useState } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000/forecast'

const FORECAST_FIELDS = [
  {
    name: 'temperature_2m_mean',
    label: 'Mean temperature',
  },
  {
    name: 'temperature_2m_max',
    label: 'Max temperature',
  },
  {
    name: 'temperature_2m_min',
    label: 'Min temperature',
  },
]

function App() {
  const [time, setTime] = useState('')
  const [city, setCity] = useState('')
  const [countryCode, setCountryCode] = useState('ru')
  const [params, setParams] = useState([])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [forecast, setForecast] = useState(null)

  const handleParamChange = (paramName) => {
    setParams((currentParams) =>
      currentParams.includes(paramName)
        ? currentParams.filter((param) => param !== paramName)
        : [...currentParams, paramName],
    )
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    setError('')
    setForecast(null)

    if (!city.trim()) {
      setError('Please enter a city name.')
      return
    }

    if (!countryCode.trim()) {
      setError('Please enter a country code.')
      return
    }

    if (!time) {
      setError('Please choose a date.')
      return
    }

    if (params.length === 0) {
      setError('Please choose at least one forecast parameter.')
      return
    }

    const searchParams = new URLSearchParams()

    searchParams.append('city', city.trim())
    searchParams.append('country_code', countryCode.trim().toLowerCase())
    searchParams.append('time', time)

    params.forEach((param) => {
      searchParams.append('params', param)
    })

    try {
      setLoading(true)

      const response = await fetch(`${API_URL}?${searchParams.toString()}`, {
        method: 'GET',
      })

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`)
      }

      const data = await response.json()
      setForecast(data)
    } catch (err) {
      setError(err.message || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <section id="center">
        <form className="forecast-form" onSubmit={handleSubmit}>
          <h1>Temperature Forecast</h1>

          <div className="form-row">
            <label htmlFor="city">City</label>
            <input
              id="city"
              type="text"
              value={city}
              onChange={(event) => setCity(event.target.value)}
              placeholder="Moscow"
            />
          </div>

          <div className="form-row">
            <label htmlFor="country-code">Country code</label>
            <input
              id="country-code"
              type="text"
              value={countryCode}
              onChange={(event) => setCountryCode(event.target.value)}
              placeholder="ru"
              maxLength={2}
            />
          </div>

          <div className="form-row">
            <label htmlFor="forecast-date">Date</label>
            <input
              id="forecast-date"
              type="date"
              value={time}
              onChange={(event) => setTime(event.target.value)}
            />
          </div>

          <fieldset className="field-group">
            <legend>Forecast parameters</legend>

            {FORECAST_FIELDS.map((field) => (
              <label key={field.name} className="checkbox-row">
                <input
                  type="checkbox"
                  checked={params.includes(field.name)}
                  onChange={() => handleParamChange(field.name)}
                />
                <span>{field.label}</span>
                <code>{field.name}</code>
              </label>
            ))}
          </fieldset>

          {error && <p className="error-message">{error}</p>}

          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Loading forecast...' : 'Get forecast'}
          </button>
        </form>

        {forecast && (
          <section className="forecast-result">
            <h2>Backend response</h2>
            <pre>{JSON.stringify(forecast, null, 2)}</pre>
          </section>
        )}
      </section>

      <div className="ticks"></div>

      <section id="next-steps">
        <div id="docs">
          <svg className="icon" role="presentation" aria-hidden="true">
            <use href="/icons.svg#documentation-icon"></use>
          </svg>
          <h2>Documentation</h2>
          <p>Your questions, answered</p>
          <ul>
            <li>
              <a
                href="https://github.com/alekselu/weather_forecast/issues"
                target="_blank"
                rel="noreferrer"
              >
                <svg
                  className="button-icon"
                  role="presentation"
                  aria-hidden="true"
                >
                  <use href="/icons.svg#github-icon"></use>
                </svg>
                GitHub
              </a>
            </li>
          </ul>
        </div>

        <div id="social">
          <svg className="icon" role="presentation" aria-hidden="true">
            <use href="/icons.svg#social-icon"></use>
          </svg>
          <h2>Connect with us</h2>
          <p>Join our community</p>
          <ul>
            <li>
              <a
                href="https://github.com/alekselu/weather_forecast"
                target="_blank"
                rel="noreferrer"
              >
                <svg
                  className="button-icon"
                  role="presentation"
                  aria-hidden="true"
                >
                  <use href="/icons.svg#github-icon"></use>
                </svg>
                GitHub
              </a>
            </li>
          </ul>
        </div>
      </section>

      <div className="ticks"></div>
      <section id="spacer"></section>
    </>
  )
}

export default App