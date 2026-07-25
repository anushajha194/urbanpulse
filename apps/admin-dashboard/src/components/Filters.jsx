import React from 'react';
import { Filter, Eye, ShieldAlert, Building2, Activity } from 'lucide-react';

export default function Filters({
  selectedDept,
  setSelectedDept,
  selectedStatus,
  setSelectedStatus,
  minSeverity,
  setMinSeverity,
  showHeatmap,
  setShowHeatmap,
  departments,
  statuses,
  activeFilterCount = 0,
  onResetFilters
}) {
  return (
    <aside className="filters-sidebar glass">
      <div className="sidebar-header">
        <div className="sidebar-header-left">
          <Filter className="sidebar-icon" size={16} />
          <h2>Control Panel</h2>
          {activeFilterCount > 0 && (
            <span className="active-filter-count">{activeFilterCount}</span>
          )}
        </div>
        {activeFilterCount > 0 && onResetFilters && (
          <button className="reset-filters-btn" onClick={onResetFilters}>
            Reset
          </button>
        )}
      </div>

      <div className="filter-group">
        <label htmlFor="dept-select">
          <Building2 size={12} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 4 }} />
          Department
        </label>
        <select
          id="dept-select"
          value={selectedDept}
          onChange={(e) => setSelectedDept(e.target.value)}
          className="form-control"
        >
          <option value="All">All Departments</option>
          {departments.map((dept) => (
            <option key={dept} value={dept}>
              {dept}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="status-select">
          <Activity size={12} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 4 }} />
          Status
        </label>
        <select
          id="status-select"
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="form-control"
        >
          <option value="All">All Statuses</option>
          {statuses.map((status) => (
            <option key={status} value={status}>
              {status.replace('_', ' ').toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <div className="slider-label">
          <label htmlFor="severity-slider">
            <ShieldAlert size={12} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 4 }} />
            Min Severity
          </label>
          <span className="slider-value">{minSeverity}</span>
        </div>
        <input
          id="severity-slider"
          type="range"
          min="0"
          max="100"
          value={minSeverity}
          onChange={(e) => setMinSeverity(Number(e.target.value))}
          className="range-slider"
        />
      </div>

      <hr className="divider" />

      <div className="toggle-group">
        <div className="toggle-label-wrapper">
          <Eye size={16} className="toggle-icon" />
          <label htmlFor="heatmap-toggle">Heatmap Overlay</label>
        </div>
        <div className="switch-wrapper">
          <input
            id="heatmap-toggle"
            type="checkbox"
            checked={showHeatmap}
            onChange={(e) => setShowHeatmap(e.target.checked)}
            className="switch-input"
          />
          <span className="switch-slider"></span>
        </div>
      </div>
    </aside>
  );
}
