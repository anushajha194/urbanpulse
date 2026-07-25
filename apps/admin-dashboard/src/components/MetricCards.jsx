import React, { useState, useEffect, useRef } from 'react';
import { AlertCircle, CheckCircle, FileText, Clock } from 'lucide-react';

// Animated counter hook
function useAnimatedCount(target, duration = 1200) {
  const [count, setCount] = useState(0);
  const prevTarget = useRef(0);

  useEffect(() => {
    const start = prevTarget.current;
    const diff = target - start;
    if (diff === 0) return;

    const startTime = performance.now();

    function animate(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(start + diff * eased));

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        prevTarget.current = target;
      }
    }

    requestAnimationFrame(animate);
  }, [target, duration]);

  return count;
}

export default function MetricCards({ complaints }) {
  const total = complaints.length;
  const pending = complaints.filter(c => c.status === 'pending' || c.status === 'under_review').length;
  
  // Breached check: status is assigned/in_progress and current time > sla_deadline
  const now = new Date();
  const breached = complaints.filter(c => 
    (c.status === 'assigned' || c.status === 'in_progress') && 
    c.sla_deadline && new Date(c.sla_deadline) < now
  ).length;

  const resolved = complaints.filter(c => c.status === 'closed' || c.status === 'verified').length;

  // Animated values
  const animTotal = useAnimatedCount(total);
  const animPending = useAnimatedCount(pending);
  const animBreached = useAnimatedCount(breached);
  const animResolved = useAnimatedCount(resolved);

  // Mock trend percentages for visual richness
  const resolutionRate = total > 0 ? ((resolved / total) * 100).toFixed(0) : 0;

  return (
    <div className="metrics-grid">
      <div className="metric-card glass accent-blue">
        <div className="metric-header">
          <span className="metric-title">Total Reports</span>
          <span className="metric-icon blue"><FileText size={18} /></span>
        </div>
        <span className="metric-value">{animTotal}</span>
        <div className="metric-footer">
          <span className="metric-desc">All civic submissions</span>
          <span className="metric-trend trend-up">↑ Live</span>
        </div>
      </div>

      <div className="metric-card glass accent-yellow">
        <div className="metric-header">
          <span className="metric-title">Awaiting Action</span>
          <span className="metric-icon yellow"><Clock size={18} /></span>
        </div>
        <span className="metric-value">{animPending}</span>
        <div className="metric-footer">
          <span className="metric-desc">Pending triage or review</span>
          {pending > 0 && (
            <span className="metric-trend trend-down">⚡ Needs attention</span>
          )}
        </div>
      </div>

      <div className="metric-card glass accent-red">
        <div className="metric-header">
          <span className="metric-title">SLA Breached</span>
          <span className="metric-icon red"><AlertCircle size={18} /></span>
        </div>
        <span className="metric-value">{animBreached}</span>
        <div className="metric-footer">
          <span className="metric-desc">Overdue for resolution</span>
          {breached > 0 && (
            <span className="metric-trend trend-down">↑ Critical</span>
          )}
        </div>
      </div>

      <div className="metric-card glass accent-green">
        <div className="metric-header">
          <span className="metric-title">Resolved</span>
          <span className="metric-icon green"><CheckCircle size={18} /></span>
        </div>
        <span className="metric-value">{animResolved}</span>
        <div className="metric-footer">
          <span className="metric-desc">Verified & closed</span>
          <span className="metric-trend trend-up">↑ {resolutionRate}%</span>
        </div>
      </div>
    </div>
  );
}
