import React, { useState, useEffect } from 'react';
import MetricCards from './components/MetricCards';
import Filters from './components/Filters';
import MapContainer from './components/MapContainer';
import ComplaintTable from './components/ComplaintTable';
import { mockComplaints } from './mockData';
import './App.css';

export default function App() {
  const [complaints, setComplaints] = useState([]);
  const [filteredComplaints, setFilteredComplaints] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filter States
  const [selectedDept, setSelectedDept] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [minSeverity, setMinSeverity] = useState(0);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [selectedComplaint, setSelectedComplaint] = useState(null);

  // Current date/time for header
  const [currentTime, setCurrentTime] = useState(new Date());

  // API Ingestion URL
  const API_URL = 'http://localhost:8001/api/v1/complaints';

  // Update clock every minute
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  // 1. Fetch data on load
  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch(API_URL);
        if (!response.ok) throw new Error('Network response not ok');
        const data = await response.json();
        if (data && data.length > 0) {
          setComplaints(data);
        } else {
          setComplaints(mockComplaints);
        }
      } catch (err) {
        console.warn('API is unreachable. Falling back to local mock database.', err);
        setComplaints(mockComplaints);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  // 2. Filter complaints dynamically when filters or base list changes
  useEffect(() => {
    let result = [...complaints];

    // Filter by Department name
    if (selectedDept !== 'All') {
      result = result.filter(c => c.department_name === selectedDept);
    }

    // Filter by Status
    if (selectedStatus !== 'All') {
      result = result.filter(c => c.status === selectedStatus);
    }

    // Filter by Minimum Severity (calculated 0-100)
    if (minSeverity > 0) {
      result = result.filter(c => c.severity_score !== null && c.severity_score >= minSeverity);
    }

    setFilteredComplaints(result);
  }, [complaints, selectedDept, selectedStatus, minSeverity]);

  // Extract unique departments and statuses for filters dropdowns dynamically
  const uniqueDepts = Array.from(
    new Set(complaints.map(c => c.department_name).filter(Boolean))
  );
  
  const uniqueStatuses = Array.from(
    new Set(complaints.map(c => c.status).filter(Boolean))
  );

  // Count active filters
  const activeFilterCount = [
    selectedDept !== 'All',
    selectedStatus !== 'All',
    minSeverity > 0
  ].filter(Boolean).length;

  const resetFilters = () => {
    setSelectedDept('All');
    setSelectedStatus('All');
    setMinSeverity(0);
  };

  const handleSelectComplaint = (complaint) => {
    setSelectedComplaint(complaint);
    // Auto toggle heatmap off to show marker highlight pulse
    setShowHeatmap(false);
    
    // Auto scroll map into view if screen size is mobile/tablet
    const mapElement = document.querySelector('.map-wrapper');
    if (mapElement) {
      mapElement.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="app-container">
      <header className="dashboard-header">
        <div className="header-left">
          <div className="header-logo">UP</div>
          <div className="header-text">
            <h1>UrbanPulse Operations</h1>
            <span className="header-subtitle">Civic Infrastructure Monitoring & Response</span>
          </div>
        </div>
        <div className="header-right">
          <div className="header-date">
            <span className="date-value">{formatDate(currentTime)}</span>
            <span>{formatTime(currentTime)}</span>
          </div>
          <div className="header-status">
            <span className="live-indicator"></span>
            <span className="live-text">Live Feed</span>
          </div>
        </div>
      </header>

      {loading ? (
        <div className="loading-container">
          <div className="skeleton-metrics">
            <div className="skeleton-card"></div>
            <div className="skeleton-card"></div>
            <div className="skeleton-card"></div>
            <div className="skeleton-card"></div>
          </div>
          <div className="skeleton-body">
            <div className="skeleton-sidebar"></div>
            <div className="skeleton-main">
              <div className="skeleton-map"></div>
              <div className="skeleton-table"></div>
            </div>
          </div>
          <div className="loading-text">
            <div className="loading-spinner"></div>
            Connecting to UrbanPulse data feed...
          </div>
        </div>
      ) : (
        <>
          {/* KPI metrics */}
          <MetricCards complaints={complaints} />

          <div className="dashboard-content">
            {/* Sidebar filters */}
            <Filters
              selectedDept={selectedDept}
              setSelectedDept={setSelectedDept}
              selectedStatus={selectedStatus}
              setSelectedStatus={setSelectedStatus}
              minSeverity={minSeverity}
              setMinSeverity={setMinSeverity}
              showHeatmap={showHeatmap}
              setShowHeatmap={setShowHeatmap}
              departments={uniqueDepts}
              statuses={uniqueStatuses}
              activeFilterCount={activeFilterCount}
              onResetFilters={resetFilters}
            />

            {/* Map and details table section */}
            <main className="main-section">
              <MapContainer
                complaints={filteredComplaints}
                showHeatmap={showHeatmap}
                selectedComplaint={selectedComplaint}
              />
              <ComplaintTable
                complaints={filteredComplaints}
                onSelectComplaint={handleSelectComplaint}
              />
            </main>
          </div>
        </>
      )}
    </div>
  );
}
