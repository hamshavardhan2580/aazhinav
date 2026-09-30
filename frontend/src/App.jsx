import { useEffect, useState } from "react";
import "./App.css";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  LayoutDashboard,
  Anchor,
  BarChart3,
  LifeBuoy,
  Thermometer,
  Wind,
  Waves,
  MapPin,
  Radio,
  Map,
  AlertTriangle,
  ClipboardList,
  ScanSearch,
  Clock,
  AlertOctagon,
  Check,
  CheckCircle2,
  Copy,
  CopyCheck,
  Navigation,
  Users,
  Gauge,
  Timer,
  Sunset,
  ShipWheel,
  Ruler,
  Activity,
  Wifi,
  WifiOff,
  ChevronRight,
  Info,
  Shield,
  Phone,
  Siren,
  ArrowRight,
  XCircle,
  AlertCircle,
} from "lucide-react";

/* =========================================================
   LIVE CLOCK
========================================================= */
function useClock() {
  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString("en-IN", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    })
  );
  useEffect(() => {
    const id = setInterval(() => {
      setTime(new Date().toLocaleTimeString("en-IN", {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      }));
    }, 1000);
    return () => clearInterval(id);
  }, []);
  return time;
}

/* =========================================================
   MAP UPDATER
========================================================= */
function MapUpdater({ latitude, longitude }) {
  const map = useMap();
  useEffect(() => {
    if (latitude !== "--" && longitude !== "--" &&
        !isNaN(Number(latitude)) && !isNaN(Number(longitude))) {
      map.setView([Number(latitude), Number(longitude)], 10);
    }
  }, [latitude, longitude, map]);

  useEffect(() => {
    // Invalidate size to prevent gray tiles on flex resize
    setTimeout(() => map.invalidateSize(), 300);
  }, [map]);
  return null;
}

/* =========================================================
   MAIN APP
========================================================= */
export default function App() {
  const clock = useClock();

  /* ── State ─────────────────────────────────────────── */
  const [activeSection, setActiveSection] = useState("dashboard");
  const [location, setLocation] = useState({ latitude: "--", longitude: "--" });
  const [weather, setWeather] = useState({ temperature: "--", windSpeed: "--", waveHeight: "--" });
  const [weatherStatus, setWeatherStatus] = useState("Acquiring live conditions…");
  const [isOnline, setIsOnline] = useState(false);

  const [boatType, setBoatType]           = useState("Small");
  const [distance, setDistance]           = useState("");
  const [departureTime, setDepartureTime] = useState("");
  const [returnTime, setReturnTime]       = useState("");
  const [crewSize, setCrewSize]           = useState("");

  const [riskScore, setRiskScore]           = useState(0);
  const [riskLevel, setRiskLevel]           = useState("UNKNOWN");
  const [riskFactors, setRiskFactors]       = useState([]);
  const [warnings, setWarnings]             = useState([]);
  const [recommendation, setRecommendation] = useState("Fill in voyage details and run a prediction.");
  const [recommendedTime, setRecommendedTime] = useState("--");
  const [subRisks, setSubRisks]             = useState(null);
  const [loading, setLoading]               = useState(false);

  const [sosTriggered, setSosTriggered]   = useState(false);
  const [locationCopied, setLocationCopied] = useState(false);
  const [toast, setToast]                   = useState(null);

  function showToast(message, type = "error") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }

  /* ── GPS ───────────────────────────────────────────── */
  useEffect(() => {
    if (!navigator.geolocation) {
      setWeatherStatus("Geolocation not supported.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        setLocation({ latitude: lat.toFixed(6), longitude: lon.toFixed(6) });
        fetchWeather(lat, lon);
      },
      () => setWeatherStatus("Unable to access GPS location."),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  }, []);

  /* ── Weather ───────────────────────────────────────── */
  async function fetchWeather(lat, lon) {
    setWeatherStatus("Loading live conditions…");
    try {
      const [wRes, mRes] = await Promise.allSettled([
        fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,wind_speed_10m&timezone=auto`),
        fetch(`https://marine-api.open-meteo.com/v1/marine?latitude=${lat}&longitude=${lon}&current=wave_height&hourly=wave_height&timezone=auto`),
      ]);
      let temperature = "--", windSpeed = "--";
      if (wRes.status === "fulfilled" && wRes.value.ok) {
        const d = await wRes.value.json();
        if (d.current) {
          if (typeof d.current.temperature_2m === "number") temperature = d.current.temperature_2m.toFixed(1);
          if (typeof d.current.wind_speed_10m === "number") windSpeed = d.current.wind_speed_10m.toFixed(1);
        }
      }
      let waveHeight = "--";
      if (mRes.status === "fulfilled" && mRes.value.ok) {
        const m = await mRes.value.json();
        if (m.current && typeof m.current.wave_height === "number") {
          waveHeight = m.current.wave_height.toFixed(2);
        } else if (m.hourly?.wave_height) {
          const v = m.hourly.wave_height.find((x) => typeof x === "number");
          if (v !== undefined) waveHeight = v.toFixed(2);
        }
      }
      setWeather({ temperature, windSpeed, waveHeight });
      setIsOnline(temperature !== "--" || windSpeed !== "--");
      setWeatherStatus(
        temperature === "--" && windSpeed === "--" ? "Weather data unavailable."
        : waveHeight === "--" ? "Weather loaded. Marine data unavailable."
        : "Live conditions updated successfully."
      );
    } catch {
      setWeatherStatus("Unable to load live conditions.");
    }
  }

  /* ── Risk calculation ──────────────────────────────── */
  async function calculateRisk() {
    if (distance === "" || parseFloat(distance) < 0) {
      showToast("Please enter a valid distance from shore.", "error");
      return;
    }
    if (crewSize === "" || parseInt(crewSize, 10) < 1) {
      showToast("Please enter a valid crew size (minimum 1).", "error");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          boat_type: boatType,
          distance_km: distance !== "" ? parseFloat(distance) : null,
          departure_time: departureTime || null,
          return_time: returnTime || null,
          crew_size: crewSize !== "" ? parseInt(crewSize, 10) : null,
          wind_speed: weather.windSpeed !== "--" ? parseFloat(weather.windSpeed) : null,
          wave_height: weather.waveHeight !== "--" ? parseFloat(weather.waveHeight) : null,
          temperature: weather.temperature !== "--" ? parseFloat(weather.temperature) : null,
          latitude: location.latitude !== "--" ? parseFloat(location.latitude) : null,
          longitude: location.longitude !== "--" ? parseFloat(location.longitude) : null,
        }),
      });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      const data = await res.json();
      setRiskScore(data.risk_score);
      setRiskLevel(data.risk_level);
      setRiskFactors(data.risk_factors);
      setWarnings(data.warnings);
      setRecommendation(data.recommendation);
      setRecommendedTime(data.recommended_time);
      setSubRisks({ sea: data.sea_risk, ocean: data.ocean_risk, cyclone: data.cyclone_risk, boat: data.boat_risk });
      setActiveSection("prediction");
    } catch (err) {
      showToast("Backend connection failed. Ensure FastAPI is running.", "error");
      setRiskLevel("UNKNOWN");
    } finally {
      setLoading(false);
    }
  }

  /* ── Helpers ───────────────────────────────────────── */
  function getRiskClass() {
    if (riskScore >= 70) return "risk-danger";
    if (riskScore >= 40) return "risk-warn";
    if (riskScore > 0)   return "risk-safe";
    return "risk-unknown";
  }
  function getGaugeClass() {
    if (riskScore >= 70) return "danger";
    if (riskScore >= 40) return "warn";
    if (riskScore > 0)   return "safe";
    return "unknown";
  }
  function normLevel(s) {
    if (!s) return "unknown";
    const l = s.toLowerCase();
    if (l === "low") return "low";
    if (l === "moderate") return "moderate";
    if (l === "high") return "high";
    return "unknown";
  }

  const CIRCUMFERENCE = 2 * Math.PI * 54;
  const dashOffset = CIRCUMFERENCE - (riskScore / 100) * CIRCUMFERENCE;
  const hasLocation = location.latitude !== "--" && location.longitude !== "--";
  const mapLat = hasLocation ? Number(location.latitude) : 13.007454;
  const mapLon = hasLocation ? Number(location.longitude) : 79.994854;
  const maxPoints = Math.max(...riskFactors.map((f) => f.points), 1);

  async function copyLocation() {
    if (!hasLocation) return;
    try {
      await navigator.clipboard.writeText(
        `AazhiNav AI Emergency Location\nLatitude: ${location.latitude}\nLongitude: ${location.longitude}`
      );
      setLocationCopied(true);
      setTimeout(() => setLocationCopied(false), 3000);
    } catch {}
  }

  /* ── Nav items ─────────────────────────────────────── */
  const navItems = [
    { id: "dashboard",  Icon: LayoutDashboard, label: "Dashboard",    badge: isOnline ? "LIVE" : null },
    { id: "voyage",     Icon: Navigation,      label: "Voyage Plan",  badge: null },
    { id: "prediction", Icon: BarChart3,        label: "Risk Analysis",badge: riskScore > 0 ? `${riskScore}%` : null },
    { id: "emergency",  Icon: LifeBuoy,         label: "Emergency",    badge: null },
  ];

  /* ── Page titles ───────────────────────────────────── */
  const pageTitles = {
    dashboard:  "Dashboard Overview",
    voyage:     "Voyage Planning",
    prediction: "Risk Analysis",
    emergency:  "Emergency Services",
  };

  /* =========================================================
     RENDER
  ========================================================= */
  return (
    <div className="app">
      {/* ── TOAST ── */}
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          {toast.type === "error" ? <XCircle size={16} strokeWidth={2.5} /> : <CheckCircle2 size={16} strokeWidth={2.5} />}
          {toast.message}
        </div>
      )}

      {/* ════════════════ SIDEBAR ════════════════ */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <Anchor size={22} strokeWidth={2} />
          </div>
          <div className="sidebar-brand">
            <h1>AazhiNav AI</h1>
            <p>Maritime Risk System</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map(({ id, Icon, label, badge }) => (
            <button
              key={id}
              className={`nav-btn ${activeSection === id ? "active" : ""}`}
              onClick={() => setActiveSection(id)}
            >
              <span className="nav-icon"><Icon size={16} strokeWidth={2} /></span>
              <span className="nav-label">{label}</span>
              {badge && <span className="nav-badge">{badge}</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-status">
            <div className="sidebar-status-dot" />
            <span>Systems Online</span>
          </div>
          <div className="sidebar-version">v1.0.0 — Open-Meteo + FastAPI</div>
        </div>
      </aside>

      {/* ════════════════ MAIN ════════════════ */}
      <div className="main-content">

        {/* ── TOP BAR ── */}
        <header className="topbar">
          <div className="topbar-left">
            <div className="topbar-title">{pageTitles[activeSection]}</div>
            <div className="topbar-sub">AI-Based Fishermen Voyage Risk Prediction</div>
          </div>
          <div className="topbar-right">
            <div className={`topbar-chip ${isOnline ? "online" : "offline"}`}>
              {isOnline
                ? <span><Wifi size={12} strokeWidth={2.5} /></span>
                : <span><WifiOff size={12} strokeWidth={2.5} /></span>}
              {isOnline ? "Live Data" : "Connecting"}
            </div>
            <div className="topbar-time">
              <span><Clock size={12} strokeWidth={2} /></span>
              {clock}
            </div>
          </div>
        </header>

        {/* ── PAGE ── */}
        <main className="page-content">

          {/* ══════════════════════════════════════
              DASHBOARD
          ══════════════════════════════════════ */}
          <section className={`section ${activeSection === "dashboard" ? "active" : ""}`}>

            {/* Stat cards */}
            <div className="stats-row">
              {[
                { Icon: Thermometer, label: "Temperature",  value: weather.temperature === "--" ? "--" : `${weather.temperature}°`, unit: "Celsius",   cls: "teal" },
                { Icon: Wind,        label: "Wind Speed",   value: weather.windSpeed === "--"   ? "--" : weather.windSpeed,          unit: "km/h",      cls: "green" },
                { Icon: Waves,       label: "Wave Height",  value: weather.waveHeight === "--"  ? "--" : weather.waveHeight,         unit: "metres",    cls: "amber" },
                { Icon: MapPin,      label: "GPS Latitude", value: hasLocation ? location.latitude : "--",                           unit: hasLocation ? "Fixed" : "Acquiring", cls: "blue" },
              ].map(({ Icon, label, value, unit, cls }) => (
                <div className="stat-card" key={label}>
                  <span className={`stat-icon ${cls}`}><Icon size={22} strokeWidth={1.8} /></span>
                  <div className="stat-info">
                    <div className="stat-value">{value}</div>
                    <div className="stat-label">{label}</div>
                    <div className={`stat-sub ${cls}`}>{unit}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Map + side panels */}
            <div className="grid-map">
              {/* Map */}
              <div className="card card-no-pad">
                <div className="card-header">
                  <div className="card-title">
                    <div className="card-title-icon"><Map size={15} strokeWidth={2} /></div>
                    Live Location Map
                  </div>
                  <span className="card-badge live">LIVE</span>
                </div>
                <div className="map-wrapper">
                  <MapContainer center={[mapLat, mapLon]} zoom={10} scrollWheelZoom className="map">
                    <MapUpdater latitude={location.latitude} longitude={location.longitude} />
                    <TileLayer
                      attribution="&copy; OpenStreetMap contributors"
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <Marker position={[mapLat, mapLon]}>
                      <Popup>
                        <strong>AazhiNav AI</strong><br />
                        {hasLocation ? `${location.latitude}, ${location.longitude}` : "Location unavailable"}
                      </Popup>
                    </Marker>
                  </MapContainer>
                </div>
              </div>

              {/* Side column */}
              <div className="side-col">
                {/* GPS */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <div className="card-title-icon"><Radio size={15} strokeWidth={2} /></div>
                      GPS Coordinates
                    </div>
                    <span className={`card-badge ${hasLocation ? "live" : "info"}`}>
                      {hasLocation ? "FIXED" : "ACQUIRING"}
                    </span>
                  </div>
                  <div className="location-list">
                    {[
                      { label: "Latitude",  value: location.latitude },
                      { label: "Longitude", value: location.longitude },
                    ].map(({ label, value }) => (
                      <div className="location-row" key={label}>
                        <span className="location-row-label">{label}</span>
                        <span className="location-row-value">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Conditions */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <div className="card-title-icon"><Activity size={15} strokeWidth={2} /></div>
                      Marine Conditions
                    </div>
                    <span className="card-badge live">LIVE</span>
                  </div>
                  <div className="conditions-grid">
                    {[
                      { Icon: Thermometer, label: "Temp",  value: weather.temperature === "--" ? "N/A" : weather.temperature, unit: "°C"   },
                      { Icon: Wind,        label: "Wind",  value: weather.windSpeed === "--"   ? "N/A" : weather.windSpeed,   unit: "km/h" },
                      { Icon: Waves,       label: "Waves", value: weather.waveHeight === "--"  ? "N/A" : weather.waveHeight,  unit: "m"    },
                    ].map(({ Icon, label, value, unit }) => (
                      <div className="condition-box" key={label}>
                        <span className="condition-box-icon"><Icon size={20} strokeWidth={1.8} /></span>
                        <div className="condition-box-label">{label}</div>
                        <div className="condition-box-value">{value}</div>
                        <div className="condition-box-unit">{unit}</div>
                      </div>
                    ))}
                  </div>
                  <div className="weather-status">
                    <div className={`weather-status-dot ${isOnline ? "" : "offline"}`} />
                    {weatherStatus}
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* ══════════════════════════════════════
              VOYAGE
          ══════════════════════════════════════ */}
          <section className={`section ${activeSection === "voyage" ? "active" : ""}`}>
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-title-icon"><ShipWheel size={15} strokeWidth={2} /></div>
                  Voyage Parameters
                </div>
                <span className="card-badge info">INPUT REQUIRED</span>
              </div>

              <div className="form-grid">
                {/* Boat type */}
                <div className="form-group">
                  <label className="form-label">
                    <Anchor size={13} strokeWidth={2.5} />
                    Boat Type
                  </label>
                  <select className="form-select" value={boatType} onChange={(e) => setBoatType(e.target.value)}>
                    <option value="Small">Small — Under 28 ft</option>
                    <option value="Medium">Medium — 28 to 40 ft</option>
                    <option value="Large">Large — 40 ft and above</option>
                  </select>
                </div>

                {/* Distance */}
                <div className="form-group">
                  <label className="form-label">
                    <Ruler size={13} strokeWidth={2.5} />
                    Distance from Shore (km)
                  </label>
                  <input
                    className="form-input" type="number" min="0" step="0.1"
                    placeholder="e.g. 25"
                    value={distance} onChange={(e) => setDistance(e.target.value)}
                  />
                </div>

                {/* Departure */}
                <div className="form-group">
                  <label className="form-label">
                    <Sunset size={13} strokeWidth={2.5} />
                    Departure Time
                  </label>
                  <input
                    className="form-input" type="time"
                    value={departureTime} onChange={(e) => setDepartureTime(e.target.value)}
                  />
                </div>

                {/* Return */}
                <div className="form-group">
                  <label className="form-label">
                    <Timer size={13} strokeWidth={2.5} />
                    Expected Return Time
                  </label>
                  <input
                    className="form-input" type="time"
                    value={returnTime} onChange={(e) => setReturnTime(e.target.value)}
                  />
                </div>

                {/* Crew */}
                <div className="form-group">
                  <label className="form-label">
                    <Users size={13} strokeWidth={2.5} />
                    Crew Size
                  </label>
                  <input
                    className="form-input" type="number" min="1" step="1"
                    placeholder="e.g. 4"
                    value={crewSize} onChange={(e) => setCrewSize(e.target.value)}
                  />
                </div>

                {/* Predict button */}
                <div className="form-group form-group-btn">
                  <button className="predict-btn" onClick={calculateRisk} disabled={loading}>
                    {loading
                      ? <><div className="spinner" /> Analyzing Voyage…</>
                      : <><BarChart3 size={16} strokeWidth={2.5} /> Run Risk Prediction</>}
                  </button>
                </div>
              </div>

              {/* Live conditions row */}
              <div className="form-conditions-row">
                <div className="section-heading">
                  <Activity size={12} strokeWidth={2.5} />
                  Live Conditions — Auto Fetched
                </div>
                <div className="conditions-grid conditions-grid-sm">
                  {[
                    { Icon: Thermometer, label: "Temperature", value: weather.temperature === "--" ? "N/A" : `${weather.temperature} °C`   },
                    { Icon: Wind,        label: "Wind Speed",  value: weather.windSpeed === "--"   ? "N/A" : `${weather.windSpeed} km/h`    },
                    { Icon: Waves,       label: "Wave Height", value: weather.waveHeight === "--"  ? "N/A" : `${weather.waveHeight} m`      },
                  ].map(({ Icon, label, value }) => (
                    <div className="condition-box" key={label}>
                      <span className="condition-box-icon"><Icon size={18} strokeWidth={1.8} /></span>
                      <div className="condition-box-label">{label}</div>
                      <div className="condition-box-value">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* ══════════════════════════════════════
              PREDICTION
          ══════════════════════════════════════ */}
          <section className={`section ${activeSection === "prediction" ? "active" : ""}`}>
            <div className="grid-2">

              {/* Left — gauge + rec */}
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

                {/* Gauge card */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <div className="card-title-icon"><Gauge size={15} strokeWidth={2} /></div>
                      Risk Assessment
                    </div>
                    <RiskBadge score={riskScore} level={riskLevel} />
                  </div>

                  <div className={`risk-hero ${getRiskClass()}`}>
                    <div className="risk-gauge-wrap">
                      <svg className="risk-gauge-svg" viewBox="0 0 120 120">
                        <circle className="risk-gauge-bg" cx="60" cy="60" r="54" />
                        <circle
                          className={`risk-gauge-fill ${getGaugeClass()}`}
                          cx="60" cy="60" r="54"
                          strokeDasharray={CIRCUMFERENCE}
                          strokeDashoffset={dashOffset}
                        />
                      </svg>
                      <div className="risk-gauge-inner">
                        <span className="risk-score-num">{riskScore}</span>
                        <span className="risk-score-pct">/ 100</span>
                      </div>
                    </div>
                    <div className="risk-level-label">{riskLevel}</div>
                    <div className="risk-level-sub">Overall voyage risk score</div>
                  </div>

                  {/* Sub-risks */}
                  {subRisks && (
                    <div className="sub-risks-wrap">
                      <div className="section-heading">
                        <BarChart3 size={11} strokeWidth={2.5} />
                        Risk Breakdown
                      </div>
                      <div className="sub-risks">
                        {[
                          { name: "Sea",     val: subRisks.sea },
                          { name: "Ocean",   val: subRisks.ocean },
                          { name: "Cyclone", val: subRisks.cyclone },
                          { name: "Boat",    val: subRisks.boat },
                        ].map(({ name, val }) => (
                          <div key={name} className="sub-risk-chip">
                            <span className="sub-risk-name">{name}</span>
                            <span className={`sub-risk-val ${normLevel(val)}`}>{val}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Recommendation */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <div className="card-title-icon"><Clock size={15} strokeWidth={2} /></div>
                      Recommendation
                    </div>
                  </div>
                  <div className="rec-box">
                    <div className="rec-time-label">Recommended Departure</div>
                    <div className="rec-time-value">{recommendedTime}</div>
                    <div className="rec-divider" />
                    <p className="rec-text">{recommendation}</p>
                  </div>
                </div>

                {/* Re-run */}
                <button className="predict-btn" onClick={calculateRisk} disabled={loading}>
                  {loading
                    ? <><div className="spinner" /> Analyzing…</>
                    : <><BarChart3 size={16} strokeWidth={2.5} /> Re-run Prediction</>}
                </button>
              </div>

              {/* Right — factors + warnings */}
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {/* Factors */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <div className="card-title-icon"><ClipboardList size={15} strokeWidth={2} /></div>
                      Risk Factors
                    </div>
                    <span className="card-badge info">{riskFactors.length} FACTORS</span>
                  </div>
                  {riskFactors.length === 0 ? (
                    <div className="empty-state">
                      <span className="empty-icon"><BarChart3 size={28} strokeWidth={1.5} /></span>
                      <p>Run a prediction to see the factor breakdown.</p>
                    </div>
                  ) : (
                    <div className="factors-table">
                      {riskFactors.map((f, i) => (
                        <div className="factor-row" key={i}>
                          <div className="factor-name">{f.name}</div>
                          <div className="factor-value">{f.value}</div>
                          <div className="factor-bar-wrap">
                            <div className="factor-bar" style={{ width: `${(f.points / maxPoints) * 100}%` }} />
                          </div>
                          <div className="factor-pts">+{f.points}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Warnings */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <div className="card-title-icon"><ScanSearch size={15} strokeWidth={2} /></div>
                      AI Warnings
                    </div>
                    <span className="card-badge info">{warnings.length}</span>
                  </div>
                  {warnings.length === 0 ? (
                    <div className="empty-state">
                      <span className="empty-icon"><CheckCircle2 size={28} strokeWidth={1.5} /></span>
                      <p>No warnings yet. Run a prediction first.</p>
                    </div>
                  ) : (
                    <div className="warnings-list">
                      {warnings.map((w, i) => {
                        const ok = ["lower-risk","Low","better","adequate","Daytime","Medium","Large"]
                          .some((kw) => w.includes(kw));
                        return (
                          <div className="warning-row" key={i}>
                            <div className={`warning-icon ${ok ? "ok" : "bad"}`}>
                              {ok
                                ? <Check size={11} strokeWidth={3} />
                                : <AlertTriangle size={11} strokeWidth={2.5} />}
                            </div>
                            <div className="warning-text">{w}</div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>

          {/* ══════════════════════════════════════
              EMERGENCY
          ══════════════════════════════════════ */}
          <section className={`section ${activeSection === "emergency" ? "active" : ""}`}>

            {/* Alert banner */}
            <div className="emergency-hero">
              <div className="emergency-hero-icon">
                <Siren size={36} strokeWidth={1.6} />
              </div>
              <div className="emergency-hero-info">
                <h2>Emergency Services</h2>
                <p>
                  If you are in distress at sea, immediately share your GPS coordinates
                  with the Indian Coast Guard or local maritime rescue authority.
                </p>
              </div>
              <div className="emergency-hero-status">
                <RiskBadge score={riskScore} level={riskLevel} />
              </div>
            </div>

            <div className="grid-2">
              {/* GPS card */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">
                    <div className="card-title-icon"><MapPin size={15} strokeWidth={2} /></div>
                    Current GPS Coordinates
                  </div>
                  <span className={`card-badge ${hasLocation ? "live" : "info"}`}>
                    {hasLocation ? "FIXED" : "ACQUIRING"}
                  </span>
                </div>

                <div className="gps-panel">
                  {[
                    { label: "Latitude",  value: location.latitude },
                    { label: "Longitude", value: location.longitude },
                  ].map(({ label, value }) => (
                    <div className="gps-block" key={label}>
                      <div className="gps-block-label">{label}</div>
                      <div className="gps-block-value">{value}</div>
                    </div>
                  ))}
                </div>

                <button className="gps-copy-btn" onClick={copyLocation} disabled={!hasLocation}>
                  {locationCopied
                    ? <><CopyCheck size={14} strokeWidth={2.5} /> Copied to Clipboard</>
                    : <><Copy size={14} strokeWidth={2.5} /> Copy GPS Coordinates</>}
                </button>

                {/* Risk status */}
                <div className="gps-risk-row">
                  <span className="gps-risk-icon"><Shield size={14} strokeWidth={2} /></span>
                  <span className="gps-risk-label">Current Risk Level</span>
                  <span className={`gps-risk-value ${getGaugeClass()}`}>{riskLevel}</span>
                </div>
              </div>

              {/* SOS + checklist */}
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <div className="card-title-icon"><AlertOctagon size={15} strokeWidth={2} /></div>
                      Emergency SOS
                    </div>
                  </div>
                  <p className="sos-desc">
                    In an emergency, press the SOS button and immediately share your
                    GPS coordinates with maritime rescue authorities.
                  </p>
                  <button
                    className={`sos-btn ${sosTriggered ? "triggered" : ""}`}
                    onClick={() => setSosTriggered(true)}
                  >
                    <Siren size={20} strokeWidth={2} />
                    {sosTriggered ? "SOS ALERT SENT" : "SEND SOS ALERT"}
                  </button>
                  {sosTriggered && (
                    <div className="sos-message">
                      <CheckCircle2 size={14} strokeWidth={2} />
                      Emergency alert prepared. Share your GPS coordinates with the appropriate authority immediately.
                    </div>
                  )}
                </div>

                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <div className="card-title-icon"><CheckCircle2 size={15} strokeWidth={2} /></div>
                      Safety Checklist
                    </div>
                  </div>
                  <div className="safety-list">
                    {[
                      "Keep your communication device fully charged",
                      "Share GPS coordinates with rescuers immediately",
                      "Wear appropriate life-saving equipment at all times",
                      "Follow instructions from maritime emergency authorities",
                      "Stay calm and signal for help using available equipment",
                    ].map((item, i) => (
                      <div className="safety-item" key={i}>
                        <div className="safety-item-check">
                          <Check size={10} strokeWidth={3} />
                        </div>
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

        </main>

        {/* ── FOOTER ── */}
        <footer className="footer">
          <span>AazhiNav AI — Maritime Risk Dashboard</span>
          <span>Open-Meteo API · FastAPI Backend · React + Vite</span>
        </footer>
      </div>
    </div>
  );
}

/* ─── Risk badge helper component ─── */
function RiskBadge({ score, level }) {
  const color = score >= 70 ? "var(--c-danger)" : score >= 40 ? "var(--c-warn)" : score > 0 ? "var(--c-safe)" : "var(--c-teal)";
  const bg    = score >= 70 ? "rgba(255,23,68,0.12)" : score >= 40 ? "rgba(255,171,64,0.12)" : score > 0 ? "rgba(0,230,118,0.12)" : "rgba(56,200,240,0.12)";
  const border= score >= 70 ? "rgba(255,23,68,0.28)" : score >= 40 ? "rgba(255,171,64,0.28)" : score > 0 ? "rgba(0,230,118,0.28)" : "rgba(56,200,240,0.28)";
  return (
    <span className="card-badge" style={{ background: bg, color, border: `1px solid ${border}` }}>
      {level}
    </span>
  );
}