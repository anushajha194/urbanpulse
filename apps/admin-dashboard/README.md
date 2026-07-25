# UrbanPulse Admin Dashboard

A React web application providing city operators with a map-based control center to filter, track, and monitor civic infrastructure complaints.

## Features

1. **GIS Map Visualization**:
   * Displays complaints as markers colored by their lifecycle status.
   * Clicking a marker displays a metadata popup card.
   * Highlighting a complaint pulses the target marker on the map.
2. **Heatmap Overlay**:
   * Toggles a heatmap layer showing density hotspots for recurring issues.
3. **Control Panel Sidebar**:
   * Filter complaints dynamically by assigned department, status, and minimum severity.
4. **Summary Metrics**:
   * Total complaints count.
   * Queue length (pending / under review).
   * Breach count (assigned or working issues past their SLA deadline).
   * Resolution count (verified / closed issues).
5. **Complaint Data Grid**:
   * Dynamic detail table with pagination, status badges, and severity indicators.

## Fallback Design Strategy

* **API Offline Fallback**: If the Ingestion API backend is offline, the React app automatically switches to an internal mock database of 10+ reports in the Delhi region, ensuring 100% interactivity for development and testing.
* **Mapbox Token Fallback**: If no Mapbox developer token is supplied, the map component displays a stylized vector coordinate overlay, supporting all markers, popups, and heatmap features without throwing WebGL errors or requiring internet access.

## Quick Start

### 1. Install dependencies
```bash
cd apps/admin-dashboard
npm install
```

### 2. Configure Token (Optional)
Create a `.env` file in `apps/admin-dashboard` and populate:
```env
VITE_MAPBOX_TOKEN=your_mapbox_api_token
```

### 3. Launch Development Server
```bash
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

## Running Tests

To run the unit tests:
```bash
npm run test
```
