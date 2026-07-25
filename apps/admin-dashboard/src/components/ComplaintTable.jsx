import React, { useState, useMemo } from 'react';
import { Calendar, ExternalLink, Search, List } from 'lucide-react';

export default function ComplaintTable({ complaints, onSelectComplaint }) {
  const [searchQuery, setSearchQuery] = useState('');

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'badge-yellow';
      case 'under_review': return 'badge-orange';
      case 'assigned': return 'badge-blue';
      case 'in_progress': return 'badge-blue-dark';
      case 'verified':
      case 'closed': return 'badge-green';
      case 'rejected': return 'badge-red';
      default: return 'badge-gray';
    }
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return 'N/A';
    return new Date(isoStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Filter complaints by search query
  const displayedComplaints = useMemo(() => {
    if (!searchQuery.trim()) return complaints;
    const q = searchQuery.toLowerCase();
    return complaints.filter(c =>
      c.issue_class.toLowerCase().includes(q) ||
      (c.department_name && c.department_name.toLowerCase().includes(q)) ||
      c.status.toLowerCase().includes(q) ||
      c.id.toLowerCase().includes(q)
    );
  }, [complaints, searchQuery]);

  if (complaints.length === 0) {
    return (
      <div className="table-empty glass">
        <List size={28} style={{ opacity: 0.3 }} />
        No complaints found matching current filter settings.
      </div>
    );
  }

  return (
    <>
      <div className="table-section-header">
        <span className="table-section-title">
          <List size={16} />
          Complaint Registry — {displayedComplaints.length} records
        </span>
        <div className="table-search-wrapper">
          <Search size={14} />
          <input
            type="text"
            className="table-search"
            placeholder="Search issues, dept..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      <div className="table-wrapper glass has-header">
        <table className="complaint-table">
          <thead>
            <tr>
              <th>Thumbnail</th>
              <th>Issue Details</th>
              <th>Department</th>
              <th>Severity</th>
              <th>Priority</th>
              <th>Status</th>
              <th>SLA Deadline</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {displayedComplaints.map((c) => (
              <tr key={c.id}>
                <td>
                  <img
                    src={c.blurred_image_url || c.image_url}
                    alt={c.issue_class}
                    className="table-thumbnail"
                    onError={(e) => {
                      e.target.src = 'https://placehold.co/60x60/161b22/484f58?text=No+Photo';
                    }}
                  />
                </td>
                <td>
                  <div className="issue-title">{c.issue_class.replace('_', ' ').toUpperCase()}</div>
                  <div className="issue-meta">
                    <span>GPS: {c.lat.toFixed(4)}, {c.lng.toFixed(4)}</span>
                  </div>
                </td>
                <td>
                  <span className="dept-text">{c.department_name || 'Awaiting Routing'}</span>
                </td>
                <td>
                  <span className={`score-badge ${c.severity_score >= 70 ? 'high-score' : c.severity_score >= 40 ? 'med-score' : 'low-score'}`}>
                    {c.severity_score ? c.severity_score.toFixed(0) : 'N/A'}
                  </span>
                </td>
                <td>
                  <span className={`score-badge ${c.priority_score >= 70 ? 'high-score' : c.priority_score >= 40 ? 'med-score' : 'low-score'}`}>
                    {c.priority_score ? c.priority_score.toFixed(0) : 'N/A'}
                  </span>
                </td>
                <td>
                  <span className={`status-badge ${getStatusColor(c.status)}`}>
                    {c.status.replace('_', ' ')}
                  </span>
                </td>
                <td>
                  <div className="sla-cell">
                    <Calendar size={14} className="sla-icon" />
                    <span>{formatDate(c.sla_deadline)}</span>
                  </div>
                </td>
                <td>
                  <button
                    onClick={() => onSelectComplaint(c)}
                    className="action-btn"
                    title="Locate on Map"
                  >
                    <ExternalLink size={13} />
                    <span>Locate</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {displayedComplaints.length === 0 && complaints.length > 0 && (
          <div className="table-empty">
            No results for "{searchQuery}"
          </div>
        )}
      </div>
    </>
  );
}
