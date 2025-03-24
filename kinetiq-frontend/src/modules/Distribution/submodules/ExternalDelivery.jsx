import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ExternalDelivery = () => {
  const [externalDeliveries, setExternalDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log("Component mounted, fetching deliveries...");
    
    // Define the API URL explicitly
    const apiUrl = 'http://localhost:8000/api/delivery/external-deliveries/';
    console.log("Requesting from:", apiUrl);
    
    axios.get(apiUrl)
      .then(response => {
        console.log('API Response:', response.data);
        setExternalDeliveries(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error details:', error);
        setError(`Failed to fetch external deliveries: ${error.message}`);
        setLoading(false);
      });
  }, []);

  // Debug rendering
  console.log("Rendering component with:", { externalDeliveries, loading, error });

  if (loading) return <div>Loading external deliveries...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div>
      <h2>External Deliveries</h2>
      <p>Status: {loading ? 'Loading...' : error ? `Error: ${error}` : `Found ${externalDeliveries.length} deliveries`}</p>
      
      {externalDeliveries.length === 0 ? (
        <p>No external deliveries found</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Delivery ID</th>
              <th>Status</th>
              <th>Content ID</th>
            </tr>
          </thead>
          <tbody>
            {externalDeliveries.map(delivery => (
              <tr key={delivery.del_order_id}>
                <td>{delivery.del_order_id}</td>
                <td>{delivery.order_status}</td>
                <td>{delivery.content_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default ExternalDelivery;