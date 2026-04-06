import './DataDisplay.css';

export default function DataDisplay({ items }) {
  if (!items || items.length === 0) return null;

  return (
    <div className="data-display mono-data">
      <div className="data-header">
        <span>Extracted Items ({items.length})</span>
        <span className="format-label">JSON Data</span>
      </div>
      <div className="data-content">
        <pre>
          {JSON.stringify(items, null, 2)}
        </pre>
      </div>
    </div>
  );
}
