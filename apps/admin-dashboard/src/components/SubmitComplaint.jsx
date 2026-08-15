import React, { useState, useRef, useCallback, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';

// Custom marker icon to avoid broken default icon
const locationIcon = new L.DivIcon({
  className: 'custom-location-marker',
  html: `<div style="
    width: 24px; height: 24px;
    background: #58a6ff;
    border: 3px solid #ffffff;
    border-radius: 50%;
    box-shadow: 0 2px 10px rgba(88,166,255,0.5);
  "></div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

// ─── EXIF GPS Extraction (client-side) ───
function extractExifGPS(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = function (e) {
      const view = new DataView(e.target.result);
      // Check for JPEG SOI marker
      if (view.getUint16(0) !== 0xFFD8) {
        resolve(null);
        return;
      }

      let offset = 2;
      while (offset < view.byteLength - 1) {
        const marker = view.getUint16(offset);
        offset += 2;

        if (marker === 0xFFE1) {
          // APP1 — EXIF data
          const length = view.getUint16(offset);
          const exifData = parseExif(view, offset + 2);
          resolve(exifData);
          return;
        } else if ((marker & 0xFF00) !== 0xFF00) {
          break;
        } else {
          offset += view.getUint16(offset);
        }
      }
      resolve(null);
    };
    reader.readAsArrayBuffer(file);
  });
}

function parseExif(view, start) {
  try {
    // Check "Exif\0\0"
    const exifHeader = String.fromCharCode(
      view.getUint8(start), view.getUint8(start + 1),
      view.getUint8(start + 2), view.getUint8(start + 3)
    );
    if (exifHeader !== 'Exif') return null;

    const tiffStart = start + 6;
    const byteOrder = view.getUint16(tiffStart);
    const littleEndian = byteOrder === 0x4949;

    const ifdOffset = view.getUint32(tiffStart + 4, littleEndian);
    const gps = findGPSInfo(view, tiffStart, tiffStart + ifdOffset, littleEndian);
    return gps;
  } catch {
    return null;
  }
}

function findGPSInfo(view, tiffStart, ifdStart, littleEndian) {
  try {
    const entries = view.getUint16(ifdStart, littleEndian);
    let gpsIFDPointer = null;

    for (let i = 0; i < entries; i++) {
      const entryStart = ifdStart + 2 + (i * 12);
      const tag = view.getUint16(entryStart, littleEndian);

      if (tag === 0x8825) {
        // GPSInfo IFD pointer
        gpsIFDPointer = view.getUint32(entryStart + 8, littleEndian);
        break;
      }
    }

    if (gpsIFDPointer === null) return null;

    const gpsStart = tiffStart + gpsIFDPointer;
    const gpsEntries = view.getUint16(gpsStart, littleEndian);

    let latRef = 'N', lngRef = 'E';
    let latValues = null, lngValues = null;

    for (let i = 0; i < gpsEntries; i++) {
      const entryStart = gpsStart + 2 + (i * 12);
      const tag = view.getUint16(entryStart, littleEndian);
      const valueOffset = view.getUint32(entryStart + 8, littleEndian);

      switch (tag) {
        case 1: // GPSLatitudeRef
          latRef = String.fromCharCode(view.getUint8(entryStart + 8));
          break;
        case 2: // GPSLatitude
          latValues = readRationals(view, tiffStart + valueOffset, 3, littleEndian);
          break;
        case 3: // GPSLongitudeRef
          lngRef = String.fromCharCode(view.getUint8(entryStart + 8));
          break;
        case 4: // GPSLongitude
          lngValues = readRationals(view, tiffStart + valueOffset, 3, littleEndian);
          break;
      }
    }

    if (latValues && lngValues) {
      let lat = latValues[0] + latValues[1] / 60 + latValues[2] / 3600;
      let lng = lngValues[0] + lngValues[1] / 60 + lngValues[2] / 3600;
      if (latRef === 'S') lat = -lat;
      if (lngRef === 'W') lng = -lng;
      return { lat, lng };
    }
    return null;
  } catch {
    return null;
  }
}

function readRationals(view, offset, count, littleEndian) {
  const values = [];
  for (let i = 0; i < count; i++) {
    const num = view.getUint32(offset + (i * 8), littleEndian);
    const den = view.getUint32(offset + (i * 8) + 4, littleEndian);
    values.push(den === 0 ? 0 : num / den);
  }
  return values;
}

// ─── Map click handler for manual location selection ───
function LocationSelector({ onSelect }) {
  useMapEvents({
    click(e) {
      onSelect({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
  });
  return null;
}

// ─── Main Component ───
export default function SubmitComplaint({ isOpen, onClose, onSubmitted }) {
  // Image states
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  // Camera states
  const [showCamera, setShowCamera] = useState(false);
  const [cameraStream, setCameraStream] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // Location states
  const [location, setLocation] = useState(null); // { lat, lng }
  const [locationSource, setLocationSource] = useState(null);
  const [locationMessage, setLocationMessage] = useState('');
  const [showMapPicker, setShowMapPicker] = useState(false);
  const [gettingDeviceLocation, setGettingDeviceLocation] = useState(false);

  // Form states
  const [issueCategory, setIssueCategory] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  const fileInputRef = useRef(null);

  const issueCategories = [
    { key: 'pothole', label: 'Pothole', icon: '🕳️' },
    { key: 'manhole', label: 'Manhole', icon: '⚠️' },
    { key: 'streetlight', label: 'Streetlight', icon: '💡' },
    { key: 'waterlogging', label: 'Waterlogging', icon: '🌊' },
    { key: 'footpath_damage', label: 'Footpath', icon: '🚶' },
    { key: 'tree', label: 'Tree', icon: '🌳' },
    { key: 'damaged_public_property', label: 'Public Property', icon: '🏚️' },
    { key: 'encroachment', label: 'Encroachment', icon: '🚧' },
  ];

  // Clean up camera stream
  useEffect(() => {
    return () => {
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [cameraStream]);

  // ─── Upload Photo ───
  const handleFileSelect = useCallback(async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    setSubmitResult(null);

    // Try to extract GPS from EXIF
    setLocationMessage('🔍 Checking image for GPS metadata...');
    const gps = await extractExifGPS(file);

    if (gps && gps.lat && gps.lng) {
      setLocation(gps);
      setLocationSource('image_exif');
      setLocationMessage(`📍 GPS location found in image metadata: ${gps.lat.toFixed(6)}, ${gps.lng.toFixed(6)}`);
    } else {
      setLocationMessage('📷 No GPS metadata found in this image. Please select a location below.');
      setLocation(null);
      setLocationSource(null);
    }
  }, []);

  // ─── Camera Capture ───
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      setCameraStream(stream);
      setShowCamera(true);
      setSubmitResult(null);

      // Attach stream to video after render
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      }, 100);
    } catch (err) {
      console.warn('Camera not available:', err);
      setLocationMessage('❌ Camera access denied or unavailable. Please upload a photo instead.');
    }
  }, []);

  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    canvas.toBlob((blob) => {
      const file = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' });
      setImageFile(file);
      setImagePreview(URL.createObjectURL(blob));
      setLocationMessage('📷 Photo captured. No EXIF GPS from camera capture — please select a location.');
      setLocation(null);
      setLocationSource(null);

      // Stop camera
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        setCameraStream(null);
      }
      setShowCamera(false);
    }, 'image/jpeg', 0.9);
  }, [cameraStream]);

  const stopCamera = useCallback(() => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
    }
    setShowCamera(false);
  }, [cameraStream]);

  // ─── Device Location ───
  const getDeviceLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationMessage('❌ Geolocation is not supported by this browser.');
      return;
    }

    setGettingDeviceLocation(true);
    setLocationMessage('🛰️ Acquiring your current location...');

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const coords = { lat: position.coords.latitude, lng: position.coords.longitude };
        setLocation(coords);
        setLocationSource('device');
        setLocationMessage(`📍 Current location detected: ${coords.lat.toFixed(6)}, ${coords.lng.toFixed(6)}`);
        setGettingDeviceLocation(false);
      },
      (error) => {
        let msg = '❌ Location access denied. ';
        if (error.code === 1) msg = '❌ Location permission denied by user.';
        else if (error.code === 2) msg = '❌ Location unavailable.';
        else if (error.code === 3) msg = '❌ Location request timed out.';
        setLocationMessage(msg + ' Please select location on the map.');
        setGettingDeviceLocation(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }, []);

  // ─── Map Location Selection ───
  const handleMapSelect = useCallback((coords) => {
    setLocation(coords);
    setLocationSource('manual');
    setLocationMessage(`📍 Location selected on map: ${coords.lat.toFixed(6)}, ${coords.lng.toFixed(6)}`);
  }, []);

  // ─── Submit ───
  const handleSubmit = useCallback(async () => {
    if (!imageFile) return;
    if (!location) {
      setLocationMessage('⚠️ Please provide a location before submitting.');
      return;
    }

    setSubmitting(true);
    setSubmitResult(null);

    try {
      const formData = new FormData();
      formData.append('image', imageFile);
      formData.append('lat', location.lat.toString());
      formData.append('lng', location.lng.toString());
      formData.append('source', 'mobile_app');
      formData.append('location_source', locationSource || 'manual');

      const response = await fetch('http://localhost:8001/api/v1/complaints', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Server responded with ${response.status}`);
      }

      const data = await response.json();
      setSubmitResult({ success: true, id: data.id, message: data.message });

      // Reset after 2 seconds and close
      setTimeout(() => {
        resetForm();
        if (onSubmitted) onSubmitted();
        if (onClose) onClose();
      }, 2000);
    } catch (err) {
      setSubmitResult({ success: false, message: err.message || 'Submission failed' });
    } finally {
      setSubmitting(false);
    }
  }, [imageFile, location, locationSource, onClose, onSubmitted]);

  const resetForm = () => {
    setImageFile(null);
    setImagePreview(null);
    setLocation(null);
    setLocationSource(null);
    setLocationMessage('');
    setShowMapPicker(false);
    setIssueCategory('');
    setDescription('');
    setSubmitResult(null);
    stopCamera();
  };

  if (!isOpen) return null;

  return (
    <div className="submit-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="submit-modal glass">
        {/* Header */}
        <div className="submit-header">
          <h2>📋 Submit Civic Report</h2>
          <button className="submit-close-btn" onClick={() => { resetForm(); onClose(); }}>✕</button>
        </div>

        <div className="submit-body">
          {/* ─── Step 1: Image Capture/Upload ─── */}
          <div className="submit-section">
            <div className="submit-section-label">
              <span className="section-step">1</span>
              CAPTURE OR UPLOAD IMAGE
            </div>

            {showCamera ? (
              <div className="camera-preview-container">
                <video ref={videoRef} autoPlay playsInline muted className="camera-video" />
                <canvas ref={canvasRef} style={{ display: 'none' }} />
                <div className="camera-controls">
                  <button className="camera-capture-btn" onClick={capturePhoto}>
                    📷 Capture
                  </button>
                  <button className="camera-cancel-btn" onClick={stopCamera}>
                    ✕ Cancel
                  </button>
                </div>
              </div>
            ) : imagePreview ? (
              <div className="image-preview-container">
                <img src={imagePreview} alt="Preview" className="image-preview" />
                <div className="preview-actions">
                  <button className="preview-action-btn" onClick={startCamera}>📷 Retake</button>
                  <button className="preview-action-btn" onClick={() => fileInputRef.current?.click()}>🖼️ Re-upload</button>
                  <button className="preview-action-btn danger" onClick={() => {
                    setImageFile(null); setImagePreview(null);
                    setLocation(null); setLocationSource(null); setLocationMessage('');
                  }}>✕ Remove</button>
                </div>
              </div>
            ) : (
              <div className="capture-buttons">
                <button className="capture-btn primary" onClick={startCamera}>
                  <span className="capture-btn-icon">📷</span>
                  <span className="capture-btn-label">Take Photo</span>
                  <span className="capture-btn-sub">Use camera</span>
                </button>
                <button className="capture-btn secondary" onClick={() => fileInputRef.current?.click()}>
                  <span className="capture-btn-icon">🖼️</span>
                  <span className="capture-btn-label">Upload Photo</span>
                  <span className="capture-btn-sub">Choose file</span>
                </button>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/tiff"
              capture="environment"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
          </div>

          {/* ─── Step 2: Location ─── */}
          {imagePreview && (
            <div className="submit-section">
              <div className="submit-section-label">
                <span className="section-step">{location ? '✓' : '2'}</span>
                LOCATION
              </div>

              {locationMessage && (
                <div className={`location-message ${location ? 'success' : ''}`}>
                  {locationMessage}
                </div>
              )}

              {!location && (
                <div className="location-actions">
                  <button
                    className="location-btn"
                    onClick={getDeviceLocation}
                    disabled={gettingDeviceLocation}
                  >
                    📍 {gettingDeviceLocation ? 'Detecting...' : 'Use Current Location'}
                  </button>
                  <button className="location-btn" onClick={() => setShowMapPicker(true)}>
                    🗺️ Select on Map
                  </button>
                </div>
              )}

              {location && !showMapPicker && (
                <div className="location-confirmed">
                  <div className="location-coords">
                    <div className="coord-item">
                      <span className="coord-label">Latitude</span>
                      <span className="coord-value">{location.lat.toFixed(6)}</span>
                    </div>
                    <div className="coord-item">
                      <span className="coord-label">Longitude</span>
                      <span className="coord-value">{location.lng.toFixed(6)}</span>
                    </div>
                    <div className="coord-item">
                      <span className="coord-label">Source</span>
                      <span className="coord-value source-badge">
                        {locationSource === 'image_exif' ? '🖼️ Image EXIF' :
                         locationSource === 'device' ? '📱 Device GPS' : '📍 Manual'}
                      </span>
                    </div>
                  </div>
                  <button className="location-change-btn" onClick={() => {
                    setShowMapPicker(true);
                  }}>
                    🗺️ Change Location
                  </button>
                </div>
              )}

              {(showMapPicker || (!location && imagePreview)) && (
                <div className="map-picker-container">
                  <div className="map-picker-hint">
                    Click on the map to select the incident location
                  </div>
                  <MapContainer
                    center={location ? [location.lat, location.lng] : [28.6139, 77.2090]}
                    zoom={location ? 16 : 13}
                    style={{ height: 220, width: '100%', borderRadius: 10 }}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
                      url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    />
                    <LocationSelector onSelect={handleMapSelect} />
                    {location && (
                      <Marker position={[location.lat, location.lng]} icon={locationIcon} />
                    )}
                  </MapContainer>
                  {location && (
                    <button className="confirm-location-btn" onClick={() => setShowMapPicker(false)}>
                      ✓ Confirm Location
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ─── Step 3: Category ─── */}
          {imagePreview && location && (
            <div className="submit-section">
              <div className="submit-section-label">
                <span className="section-step">{issueCategory ? '✓' : '3'}</span>
                ISSUE CATEGORY
              </div>
              <div className="category-grid">
                {issueCategories.map((cat) => (
                  <button
                    key={cat.key}
                    className={`category-chip ${issueCategory === cat.key ? 'active' : ''}`}
                    onClick={() => setIssueCategory(cat.key)}
                  >
                    <span>{cat.icon}</span>
                    <span>{cat.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ─── Submit Result ─── */}
          {submitResult && (
            <div className={`submit-result ${submitResult.success ? 'success' : 'error'}`}>
              {submitResult.success ? (
                <>✅ {submitResult.message} <span className="result-id">ID: {submitResult.id}</span></>
              ) : (
                <>❌ {submitResult.message}</>
              )}
            </div>
          )}

          {/* ─── Submit Button ─── */}
          {imagePreview && location && (
            <button
              className={`submit-complaint-btn ${submitting ? 'submitting' : ''}`}
              onClick={handleSubmit}
              disabled={submitting || !imageFile || !location}
            >
              {submitting ? '⏳ Submitting...' : '🚀 Submit Complaint'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
