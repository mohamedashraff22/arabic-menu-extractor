import { useState } from 'react';
import { apiClient } from '../api/client';
import './MenuUploader.css';

export default function MenuUploader({ onUploadComplete }) {
  const [file, setFile] = useState(null);
  const [restaurantName, setRestaurantName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !restaurantName) return;

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('restaurant_name', restaurantName);

    try {
      const response = await apiClient.post('/menus/upload', formData, true);
      onUploadComplete(response);
      setFile(null);
      setRestaurantName('');
    } catch (err) {
      setError(err.message || 'Error uploading menu');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="panel menu-uploader">
      <h3>Analyze New Menu</h3>
      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <label htmlFor="restaurant-name">Restaurant Name</label>
          <input
            id="restaurant-name"
            type="text"
            required
            placeholder="e.g. مطعم الشامي"
            value={restaurantName}
            onChange={(e) => setRestaurantName(e.target.value)}
          />
        </div>
        
        <div className="input-group">
          <label htmlFor="menu-file">Menu Image</label>
          <input
            id="menu-file"
            type="file"
            accept="image/*"
            required
            onChange={handleFileChange}
          />
        </div>

        {error && <div className="error-msg">{error}</div>}

        <button 
          type="submit" 
          className="btn-primary upload-btn"
          disabled={isUploading || !file || !restaurantName}
        >
          {isUploading ? 'Extracting via AI...' : 'Upload & Extract'}
        </button>
      </form>
    </div>
  );
}
