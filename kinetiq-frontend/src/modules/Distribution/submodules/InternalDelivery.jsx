import React, { useState, useEffect } from 'react';
import axios from 'axios';

const InternalDelivery = () => {
  const [internalDeliveries, setInternalDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log("Component mounted, fetching internal deliveries...");
    
    // Define the API URL
    const apiUrl = 'http://localhost:8000/api/delivery/internal-deliveries/';
    console.log("Requesting from:", apiUrl);
    
    axios.get(apiUrl)
      .then(response => {
        console.log('API Response:', response.data);
        setInternalDeliveries(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error details:', error);
        setError(`Failed to fetch internal deliveries: ${error.message}`);
        setLoading(false);
      });
  }, []);

  console.log("Rendering component with:", { internalDeliveries, loading, error });

  if (loading) return <div>Loading internal deliveries...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div>
      <h2>Internal Deliveries</h2>
      <p>Status: {loading ? 'Loading...' : error ? `Error: ${error}` : `Found ${internalDeliveries.length} deliveries`}</p>
      
      {internalDeliveries.length === 0 ? (
        <p>No internal deliveries found</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Delivery ID</th>
              <th>Status</th>
              <th>Content ID</th>
              <th>Project Based</th>
              <th>Partial Delivery</th>
            </tr>
          </thead>
          <tbody>
            {internalDeliveries.map(delivery => (
              <tr key={delivery.del_order_id}>
                <td>{delivery.del_order_id}</td>
                <td>{delivery.order_status}</td>
                <td>{delivery.content_id}</td>
                <td>{delivery.is_project_based === 'true' ? 'Yes' : 'No'}</td>
                <td>{delivery.is_partial_delivery === 'true' ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default InternalDelivery;