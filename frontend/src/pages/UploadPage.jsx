import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import MenuUploader from '../components/MenuUploader';
import DataDisplay from '../components/DataDisplay';
import { apiClient } from '../api/client';
import './UploadPage.css';

export default function UploadPage() {
  const [menus, setMenus] = useState([]);
  const [recentUpload, setRecentUpload] = useState(null);
  const navigate = useNavigate();

  const loadMenus = async () => {
    try {
      const data = await apiClient.get('/menus');
      setMenus(data.menus || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadMenus();
  }, []);

  const handleUploadComplete = async (response) => {
    try {
      const detailed = await apiClient.get(`/menus/${response.menu_id}`);
      setRecentUpload(detailed);
      loadMenus(); 
    } catch (err) {
      console.error('Failed to fetch full menu details', err);
    }
  };

  const deleteMenu = async (menuId) => {
    try {
      await apiClient.delete(`/menus/${menuId}`);
      if (recentUpload?.menu_id === menuId) {
        setRecentUpload(null);
      }
      loadMenus();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="upload-page">
      <header className="page-header hero-header">
        <div className="hero-badge">AI Powered OCR</div>
        <h1>Extract & Chat with Arabic Menus</h1>
        <p className="subtitle">Upload high-resolution restaurant menus to instantly digitize them and unlock an intelligent conversational agent.</p>
      </header>

      <div className="upload-grid">
        <div className="upload-section">
          <MenuUploader onUploadComplete={handleUploadComplete} />
          
          {recentUpload && (
            <div className="recent-upload-info panel">
              <div className="recent-header">
                <div>
                  <h4 style={{ color: 'var(--accent-primary)', marginBottom: '4px' }}>Extracted Successfully</h4>
                  <strong style={{ fontSize: '1.2rem'}}>{recentUpload.restaurant_name}</strong>
                </div>
                <button 
                  className="btn-primary" 
                  onClick={() => navigate(`/chat/${recentUpload.menu_id}`)}
                >
                  Start Chat Session ✨
                </button>
              </div>
              <p className="text-muted" style={{ marginBottom: '1rem'}}>Found {recentUpload.item_count} items</p>
              
              <DataDisplay items={recentUpload.items} />
            </div>
          )}
        </div>

        <div className="menus-list-section panel">
          <h3>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 6h16M4 12h16M4 18h7"/></svg>
            Menu Library
          </h3>
          {menus.length === 0 ? (
            <p className="empty-state">No menus uploaded yet. Upload a menu to get started.</p>
          ) : (
            <ul className="menu-list">
              {menus.map(m => (
                <li key={m.menu_id} className="menu-card">
                  <div className="menu-card-info">
                    <strong>{m.restaurant_name}</strong>
                    <span className="mono-data text-muted">{m.item_count} items extracted</span>
                  </div>
                  <div className="menu-card-actions">
                    <button className="btn-secondary" style={{ padding: '0.4rem 1rem', fontSize: '0.875rem'}} onClick={() => navigate(`/chat/${m.menu_id}`)}>Chat</button>
                    <button className="btn-danger" onClick={() => deleteMenu(m.menu_id)}>Delete</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
