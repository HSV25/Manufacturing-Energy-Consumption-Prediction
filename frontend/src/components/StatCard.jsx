import React from 'react';

export default function StatCard({ label, value, subtext, icon, color = 'blue' }) {
  return (
    <div className="stat-card">
      <div className="stat-info">
        <span className="stat-label">{label}</span>
        <span className="stat-value">{value ?? '—'}</span>
        {subtext && <span className="stat-subtext">{subtext}</span>}
      </div>
      <div className={`stat-icon ${color}`}>
        {icon}
      </div>
    </div>
  );
}
