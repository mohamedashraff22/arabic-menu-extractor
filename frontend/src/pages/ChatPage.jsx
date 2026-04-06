import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ChatBox from '../components/ChatBox';
import { apiClient, BASE_URL } from '../api/client';
import './ChatPage.css';

export default function ChatPage() {
  const { menuId } = useParams();
  const navigate = useNavigate();
  const [menuDetails, setMenuDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isImageOpen, setIsImageOpen] = useState(false);

  useEffect(() => {
    const fetchDetailedMenu = async () => {
      try {
        const data = await apiClient.get(`/menus/${menuId}`);
        setMenuDetails(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    if (menuId) {
      fetchDetailedMenu();
    }
  }, [menuId]);

  return (
    <div className="chat-page">
      <header className="page-header chat-page-header">
        <button className="btn-secondary back-btn" onClick={() => navigate(-1)}>
          ← Back to Menus
        </button>
        <div>
          <h2>Menu Session</h2>
        </div>
      </header>

      {loading ? (
        <div className="loading-state">Loading context...</div>
      ) : !menuDetails ? (
        <div className="error-state">Error: Menu context not found.</div>
      ) : (
        <div className="chat-layout">
          <div className="chat-wrapper">
            <ChatBox menuId={menuDetails.menu_id} restaurantName={menuDetails.restaurant_name} />
          </div>
          <div className="sidebar-wrapper">
            <div className="panel side-panel">
              <h4>{menuDetails.restaurant_name}</h4>
              <p className="text-muted" style={{ marginBottom: '1rem'}}>Total items: {menuDetails.item_count}</p>
              
              <div className="data-display" style={{ marginTop: '1rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
                <div className="data-header">
                  <span>Menu Document</span>
                  <span className="format-label">Image</span>
                </div>
                <div 
                  className="menu-image-container" 
                  onClick={() => setIsImageOpen(true)}
                  style={{ border: 'none', borderRadius: 0, marginBottom: 0, height: '350px', background: '#000' }}
                >
                  <img 
                    src={`${BASE_URL}/menus/${menuDetails.menu_id}/image`} 
                    alt="Menu" 
                    onError={(e) => { e.target.style.display = 'none'; }}
                  />
                  <div className="zoom-hint">🔍 View Full Size</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {isImageOpen && menuDetails && (
        <div className="lightbox" onClick={() => setIsImageOpen(false)}>
          <div className="lightbox-content">
            <button className="close-lightbox" onClick={() => setIsImageOpen(false)}>✕</button>
            <img src={`${BASE_URL}/menus/${menuDetails.menu_id}/image`} alt="Full size Menu" />
          </div>
        </div>
      )}
    </div>
  );
}
