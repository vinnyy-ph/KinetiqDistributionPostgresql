// Packing.jsx
import React, { useState, useEffect } from "react";
import "../styles/Packing.css";
import PackingTable from "../components/packing/PackingTable";
import StatusFilter from "../components/packing/StatusFilter";
import TypeFilter from "../components/packing/TypeFilter";
import CompletionModal from "../components/packing/CompletionModal";
import EditPackingModal from "../components/packing/EditPackingModal";

const Packing = () => {
  // State for data management
  const [packingLists, setPackingLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [packingTypes, setPackingTypes] = useState([]);
  
  // State for filtering
  const [statusFilter, setStatusFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");
  const [searchTerm, setSearchTerm] = useState("");
  
  // State for action management
  const [selectedList, setSelectedList] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showCompletionModal, setShowCompletionModal] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Fetch data on component mount and when refreshTrigger changes
  useEffect(() => {
    const fetchPackingLists = async () => {
      try {
        setLoading(true);
        setError(null); // Reset error state
        const response = await fetch('http://127.0.0.1:8000/api/packing-lists/');
        
        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('Authentication error. Please login again.');
          } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch packing lists');
          }
        }
        
        const data = await response.json();
        setPackingLists(data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
        console.error('Error fetching packing lists:', err);
      }
    };

    const fetchEmployees = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/employees/');
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch employees');
        }
        
        const data = await response.json();
        setEmployees(data);
      } catch (err) {
        console.error('Error fetching employees:', err);
      }
    };

    const fetchPackingTypes = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/packing-types/');
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch packing types');
        }
        
        const data = await response.json();
        setPackingTypes(data);
      } catch (err) {
        console.error('Error fetching packing types:', err);
      }
    };

    fetchPackingLists();
    fetchEmployees();
    fetchPackingTypes();
  }, [refreshTrigger]);
  
  // Handle search input change
  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };
  
  // Handle status filter change
  const handleStatusFilterChange = (status) => {
    setStatusFilter(status);
  };
  
  // Handle type filter change
  const handleTypeFilterChange = (type) => {
    setTypeFilter(type);
  };
  
  // Apply filters to packing lists
  const filteredLists = packingLists.filter(list => {
    // Apply status filter
    if (statusFilter !== "All" && list.packing_status !== statusFilter) {
      return false;
    }
    
    // Apply type filter
    if (typeFilter !== "All" && list.packing_type !== typeFilter) {
      return false;
    }
    
    // Apply search filter (search by packing_list_id or delivery_id)
    if (searchTerm && !list.packing_list_id.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !String(list.delivery_id || '').toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    
    return true;
  });
  
  // Handle list selection - now opens the edit modal
  const handleListSelect = (list) => {
    setSelectedList(list);
    setShowEditModal(true);
  };
  
  // Handle closing the edit modal
  const handleCloseEditModal = () => {
    setShowEditModal(false);
  };
  
  // Handle save changes from the edit modal
  const handleSaveChanges = async (list, updates) => {
    if (Object.keys(updates).length === 0) {
      setShowEditModal(false);
      return;
    }
    
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/packing-lists/${list.packing_list_id}/update/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update packing list');
      }
      
      // Refresh the list after successful update
      setRefreshTrigger(prev => prev + 1);
      setShowEditModal(false);
      
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };
  
  // Handle status update
  const handleStatusUpdate = async (list, newStatus) => {
    try {
      // If trying to mark as Packed, show the confirmation modal first
      if (newStatus === 'Packed') {
        setShowEditModal(false);
        setShowCompletionModal(true);
        return;
      }
      
      const response = await fetch(`http://127.0.0.1:8000/api/packing-lists/${list.packing_list_id}/update/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          packing_status: newStatus
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update packing list status');
      }
      
      // Refresh the list after successful update
      setRefreshTrigger(prev => prev + 1);
      setShowEditModal(false);
      
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };
  
  // Handle completion confirmation
  const handleConfirmCompletion = async () => {
    if (!selectedList) return;
    
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/packing-lists/${selectedList.packing_list_id}/update/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          packing_status: 'Packed'
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to complete packing list');
      }
      
      // Close modal and refresh the list
      setShowCompletionModal(false);
      setRefreshTrigger(prev => prev + 1);
      
      // Show success notification
      alert('Packing list marked as Packed successfully! A new Shipment has been created.');
      
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };
  
  return (
    <div className="packing">
      <div className="body-content-container">
        <h2 className="page-title">Packing Lists</h2>
        
        {/* Filters Row */}
        <div className="filters-row">
          <div className="search-container">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              className="search-input"
              placeholder="Search by Packing ID or Delivery ID..."
              value={searchTerm}
              onChange={handleSearchChange}
            />
          </div>
          
          <StatusFilter 
            selectedStatus={statusFilter}
            onStatusChange={handleStatusFilterChange}
          />
          
          <TypeFilter 
            packingTypes={packingTypes}
            selectedType={typeFilter}
            onTypeChange={handleTypeFilterChange}
          />
        </div>
        
        {/* Statistics Row */}
        <div className="stats-row">
          <div className="stat-box">
            <span className="stat-label">Total Lists:</span>
            <span className="stat-value">{packingLists.length}</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Pending:</span>
            <span className="stat-value">
              {packingLists.filter(list => list.packing_status === 'Pending').length}
            </span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Packed:</span>
            <span className="stat-value">
              {packingLists.filter(list => list.packing_status === 'Packed').length}
            </span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Shipped:</span>
            <span className="stat-value">
              {packingLists.filter(list => list.packing_status === 'Shipped').length}
            </span>
          </div>
        </div>
        
        {/* Packing Table */}
        {loading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Loading packing lists...</p>
          </div>
        ) : error ? (
          <div className="error-container">
            <p className="error-message">Error: {error}</p>
          </div>
        ) : (
          <div className="packing-content">
            <PackingTable 
              packingLists={filteredLists} 
              onListSelect={handleListSelect} 
              selectedList={selectedList}
              employees={employees}
            />
          </div>
        )}
        
        {/* Edit Modal */}
        {showEditModal && selectedList && (
          <EditPackingModal 
            packingList={selectedList}
            employees={employees}
            packingTypes={packingTypes}
            onClose={handleCloseEditModal}
            onSave={handleSaveChanges}
            onStatusUpdate={handleStatusUpdate}
          />
        )}
        
        {/* Completion Confirmation Modal */}
        {showCompletionModal && selectedList && (
          <CompletionModal 
            packingList={selectedList}
            onConfirm={handleConfirmCompletion}
            onCancel={() => setShowCompletionModal(false)}
          />
        )}
      </div>
    </div>
  );
};

export default Packing;