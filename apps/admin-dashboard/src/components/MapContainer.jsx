import React, { useEffect, useMemo } from 'react';
import { MapContainer as LeafletMapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import { Map, AlertTriangle } from 'lucide-react';

// Status → color mapping (consistent with the rest of the dashboard)
const getMarkerColor = (status) => {
  switch (status) {
    case 'pending': return '#d29922';
    case 'under_review': return '#f0883e';
    case 'assigned': return '#58a6ff';
    case 'in_progress': return '#1f6feb';
    case 'verified':
    case 'closed': return '#3fb950';
    case 'rejected': return '#f85149';
    default: return '#8b949e';
  }
};

// Helper component to auto-fit map bounds to markers
function FitBounds({ complaints, selectedComplaint }) {
  const map = useMap();

  useEffect(() => {
    if (selectedComplaint) {
      map.setView([selectedComplaint.lat, selectedComplaint.lng], 16, { animate: true });
      return;
    }

    if (complaints.length > 0) {
      const bounds = complaints.map(c => [c.lat, c.lng]);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    }
  }, [complaints, selectedComplaint, map]);

  return null;
}

export default function MapContainer({ complaints, showHeatmap, selectedComplaint }) {
  // Default center: Delhi (matches mock data coordinates)
  const defaultCenter = [28.6139, 77.2090];
  const defaultZoom = 14;

  // Determine center from complaints or use default
  const center = useMemo(() => {
    if (complaints.length === 0) return defaultCenter;
    const avgLat = complaints.reduce((sum, c) => sum + c.lat, 0) / complaints.length;
    const avgLng = complaints.reduce((sum, c) => sum + c.lng, 0) / complaints.length;
    return [avgLat, avgLng];
  }, [complaints]);

  return (
    <div>
      <div className="map-section-header">
        <span className="map-section-title">
          <Map size={16} />
          GIS Incident Map
        </span>
        <span className="map-complaint-count">
          {complaints.length} incident{complaints.length !== 1 ? 's' : ''} mapped
        </span>
      </div>
      <div className="map-wrapper glass has-header">
        {complaints.length === 0 ? (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 8, color: 'var(--text-muted)' }}>
            <AlertTriangle size={32} style={{ opacity: 0.3 }} />
            <span>No incidents match current filters</span>
          </div>
        ) : (
          <LeafletMapContainer
            center={center}
            zoom={defaultZoom}
            style={{ height: '100%', width: '100%', borderRadius: '0 0 14px 14px' }}
            zoomControl={true}
            attributionControl={true}
          >
            {/* Dark-themed tile layer for premium look */}
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />

            {/* Auto-fit bounds */}
            <FitBounds complaints={complaints} selectedComplaint={selectedComplaint} />

            {/* Heatmap overlay — larger translucent circles */}
            {showHeatmap && complaints.map((c) => (
              <CircleMarker
                key={`heat-${c.id}`}
                center={[c.lat, c.lng]}
                radius={35}
                pathOptions={{
                  color: 'transparent',
                  fillColor: '#f85149',
                  fillOpacity: 0.2,
                }}
              />
            ))}

            {/* Complaint markers */}
            {!showHeatmap && complaints.map((c) => {
              const isSelected = selectedComplaint && selectedComplaint.id === c.id;
              const markerColor = getMarkerColor(c.status);
              return (
                <CircleMarker
                  key={c.id}
                  center={[c.lat, c.lng]}
                  radius={isSelected ? 12 : 8}
                  pathOptions={{
                    color: '#ffffff',
                    weight: isSelected ? 3 : 2,
                    fillColor: markerColor,
                    fillOpacity: 0.9,
                  }}
                >
                  <Popup>
                    <div style={{
                      fontFamily: 'Inter, sans-serif',
                      minWidth: 180,
                    }}>
                      <div style={{
                        fontWeight: 700,
                        fontSize: 13,
                        marginBottom: 6,
                        color: '#1a1a2e',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>
                        {c.issue_class.replace(/_/g, ' ')}
                      </div>
                      {(c.blurred_image_url || c.image_url) && (
                        <img
                          src={c.blurred_image_url || c.image_url}
                          alt={c.issue_class}
                          style={{
                            width: '100%',
                            height: 80,
                            objectFit: 'cover',
                            borderRadius: 6,
                            marginBottom: 8,
                          }}
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      )}
                      <div style={{ fontSize: 12, lineHeight: 1.8 }}>
                        <div>
                          <span style={{ color: '#6b7280' }}>Status: </span>
                          <span style={{ color: markerColor, fontWeight: 600 }}>
                            {c.status.replace(/_/g, ' ').toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <span style={{ color: '#6b7280' }}>Severity: </span>
                          <strong>{c.severity_score ? c.severity_score.toFixed(0) : 'N/A'}</strong>
                        </div>
                        <div>
                          <span style={{ color: '#6b7280' }}>Dept: </span>
                          <span>{c.department_name || 'Awaiting Routing'}</span>
                        </div>
                        <div style={{ marginTop: 4, fontSize: 11, color: '#9ca3af' }}>
                          📍 {c.lat.toFixed(5)}, {c.lng.toFixed(5)}
                        </div>
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </LeafletMapContainer>
        )}

        {/* Legend overlay */}
        <div className="map-legend glass" style={{ zIndex: 1000 }}>
          <h4>Legend</h4>
          <div className="legend-row"><span className="legend-dot" style={{ backgroundColor: '#d29922' }} /><span>Pending</span></div>
          <div className="legend-row"><span className="legend-dot" style={{ backgroundColor: '#f0883e' }} /><span>Under Review</span></div>
          <div className="legend-row"><span className="legend-dot" style={{ backgroundColor: '#58a6ff' }} /><span>Assigned</span></div>
          <div className="legend-row"><span className="legend-dot" style={{ backgroundColor: '#1f6feb' }} /><span>In Progress</span></div>
          <div className="legend-row"><span className="legend-dot" style={{ backgroundColor: '#3fb950' }} /><span>Closed/Verified</span></div>
          <div className="legend-row"><span className="legend-dot" style={{ backgroundColor: '#f85149' }} /><span>Rejected</span></div>
        </div>
      </div>
    </div>
  );
}
