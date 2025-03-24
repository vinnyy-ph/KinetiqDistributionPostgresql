import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Picking = () => {
  const [pickingLists, setPickingLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log("Component mounted, fetching picking lists...");
    
    const apiUrl = 'http://localhost:8000/api/picking/picking-lists/';
    console.log("Requesting from:", apiUrl);
    
    axios.get(apiUrl)
      .then(response => {
        console.log('API Response:', response.data);
        setPickingLists(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error details:', error);
        setError(`Failed to fetch picking lists: ${error.message}`);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading picking lists...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div>
      <h2>Picking Lists</h2>
      <p>Status: {loading ? 'Loading...' : error ? `Error: ${error}` : `Found ${pickingLists.length} picking lists`}</p>
      
      {pickingLists.length === 0 ? (
        <p>No picking lists found</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Picking List ID</th>
              <th>Warehouse ID</th>
              <th>Picked By</th>
              <th>Picking Status</th>
              <th>Picked Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pickingLists.map(list => (
              <tr key={list.picking_list_id}>
                <td>{list.picking_list_id}</td>
                <td>{list.warehouse_id || 'Not assigned'}</td>
                <td>{list.picked_by || 'Not assigned'}</td>
                <td>{list.picked_status}</td>
                <td>{list.picked_date || 'Not picked yet'}</td>
                <td>
                  <button onClick={() => console.log('Process picking list', list.picking_list_id)}>
                    Process
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default Picking;