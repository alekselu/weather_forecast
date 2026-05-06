// import { useState } from 'react'
// import reactLogo from './assets/react.svg'
// import viteLogo from './assets/vite.svg'
// import heroImg from './assets/hero.png'
// import './App.css'

// function App() {
//   const [count, setCount] = useState(0)

//   return (
//     <>
//       <section id="center">
//         <button
//           type="button"
//           className="counter"
//           onClick={() => setCount((count) => count + 1)}
//         >
//           Count is {count}
//         </button>
//       </section>

//       <div className="ticks"></div>

//       <section id="next-steps">
//         <div id="docs">
//           <svg className="icon" role="presentation" aria-hidden="true">
//             <use href="/icons.svg#documentation-icon"></use>
//           </svg>
//           <h2>Documentation</h2>
//           <p>Your questions, answered</p>
//           <ul>
//             <a href="https://github.com/alekselu/weather_forecast/issues" target="_blank">
//               <svg
//                 className="button-icon"
//                 role="presentation"
//                 aria-hidden="true"
//               >
//                 <use href="/icons.svg#github-icon"></use>
//               </svg>
//               GitHub
//             </a>
//           </ul>
//         </div>
//         <div id="social">
//           <svg className="icon" role="presentation" aria-hidden="true">
//             <use href="/icons.svg#social-icon"></use>
//           </svg>
//           <h2>Connect with us</h2>
//           <p>Join our community</p>
//           <ul>
//             <li>
//               <a href="https://github.com/alekselu/weather_forecast" target="_blank">
//                 <svg
//                   className="button-icon"
//                   role="presentation"
//                   aria-hidden="true"
//                 >
//                   <use href="/icons.svg#github-icon"></use>
//                 </svg>
//                 GitHub
//               </a>
//             </li>

//           </ul>
//         </div>
//       </section>

//       <div className="ticks"></div>
//       <section id="spacer"></section>
//     </>
//   )
// }

// export default App
import { useState } from 'react'
import './App.css'

const API_URL = '/api/forecast'

const DAILY_FIELDS = [
  {
    name: 'temperature_2m_mean',
    label: 'Daily mean temperature',
  },
  {
    name: 'temperature_2m_min',
    label: 'Daily minimum temperature',
  },
  {
    name: 'temperature_2m_max',
    label: 'Daily maximum temperature',
  },
]

const HOURLY_FIELDS = [
  {
    name: 'temperature_2m',
    label: 'Hourly temperature',
  },
]

function App() {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const [dailyFields, setDailyFields] = useState([])
  const [hourlyFields, setHourlyFields] = useState([])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [forecast, setForecast] = useState(null)

  const handleDailyFieldChange = (fieldName) => {
    setDailyFields((currentFields) =>
      currentFields.includes(fieldName)
        ? currentFields.filter((field) => field !== fieldName)
        : [...currentFields, fieldName],
    )
  }

  const handleHourlyFieldChange = (fieldName) => {
    setHourlyFields((currentFields) =>
      currentFields.includes(fieldName)
        ? currentFields.filter((field) => field !== fieldName)
        : [...currentFields, fieldName],
    )
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    setError('')
    setForecast(null)

    if (!startDate || !endDate) {
      setError('Please choose start date and end date.')
      return
    }

    if (new Date(startDate) > new Date(endDate)) {
      setError('Start date cannot be later than end date.')
      return
    }

    if (dailyFields.length === 0 && hourlyFields.length === 0) {
      setError('Please choose at least one forecast field.')
      return
    }

    const payload = {
      start_date: startDate,
      end_date: endDate,
      daily: dailyFields,
      hourly: hourlyFields,
    }

    try {
      setLoading(true)

      const response = await fetch(API_URL, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
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
            <label htmlFor="start-date">Start date</label>
            <input
              id="start-date"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </div>

          <div className="form-row">
            <label htmlFor="end-date">End date</label>
            <input
              id="end-date"
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </div>

          <fieldset className="field-group">
            <legend>Daily fields</legend>

            {DAILY_FIELDS.map((field) => (
              <label key={field.name} className="checkbox-row">
                <input
                  type="checkbox"
                  checked={dailyFields.includes(field.name)}
                  onChange={() => handleDailyFieldChange(field.name)}
                />
                <span>{field.label}</span>
                <code>{field.name}</code>
              </label>
            ))}
          </fieldset>

          <fieldset className="field-group">
            <legend>Hourly fields</legend>

            {HOURLY_FIELDS.map((field) => (
              <label key={field.name} className="checkbox-row">
                <input
                  type="checkbox"
                  checked={hourlyFields.includes(field.name)}
                  onChange={() => handleHourlyFieldChange(field.name)}
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