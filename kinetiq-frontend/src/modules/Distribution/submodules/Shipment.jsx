// Shipment.jsx
import React, { useState, useEffect } from "react";
import "../styles/Shipment.css";
import ShipmentTable from "../components/shipment/ShipmentTable";
import FailedShipmentsTable from "../components/shipment/FailedShipmentsTable";
import StatusFilter from "../components/shipment/StatusFilter";
import CarrierFilter from "../components/shipment/CarrierFilter";
import DeliveryTypeFilter from "../components/shipment/DeliveryTypeFilter";
import ShipmentModal from "../components/shipment/ShipmentModal";
import ConfirmShipModal from "../components/shipment/ConfirmShipModal";
import DeliveryReceiptModal from "../components/shipment/DeliveryReceiptModal";
import FailureReportModal from "../components/shipment/FailureReportModal";
import CarrierManagementModal from "../components/shipment/CarrierManagementModal";

const Shipment = () => {
  // New tab state
  const [activeTab, setActiveTab] = useState("shipments"); // "shipments" or "failed"
  
  // State for data management
  const [shipments, setShipments] = useState([]);
  const [failedShipments, setFailedShipments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [carriers, setCarriers] = useState([]);
  
  // State for filtering
  const [statusFilter, setStatusFilter] = useState("All");
  const [carrierFilter, setCarrierFilter] = useState("All");
  const [deliveryTypeFilter, setDeliveryTypeFilter] = useState("All");
  const [searchTerm, setSearchTerm] = useState("");
  
  // State for action management
  const [selectedShipment, setSelectedShipment] = useState(null);
  const [showShipmentModal, setShowShipmentModal] = useState(false);
  const [showConfirmShipModal, setShowConfirmShipModal] = useState(false);
  const [showDeliveryReceiptModal, setShowDeliveryReceiptModal] = useState(false);
  const [showFailureReportModal, setShowFailureReportModal] = useState(false);
  const [showCarrierManagementModal, setShowCarrierManagementModal] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Fetch data on component mount and when refreshTrigger changes
  useEffect(() => {
    const fetchShipments = async () => {
      try {
        setLoading(true);
        setError(null); // Reset error state
        const response = await fetch('http://127.0.0.1:8000/api/shipments/');
        
        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('Authentication error. Please login again.');
          } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch shipments');
          }
        }
        
        const data = await response.json();
        
        // Separate regular shipments and failed shipments
        const failed = data.filter(s => s.shipment_status === 'Failed');
        const regular = data.filter(s => s.shipment_status !== 'Failed');
        
        setShipments(regular);
        setFailedShipments(failed);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
        console.error('Error fetching shipments:', err);
      }
    };

    const fetchCarriers = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/carriers/');
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch carriers');
        }
        
        const data = await response.json();
        setCarriers(data);
      } catch (err) {
        console.error('Error fetching carriers:', err);
      }
    };

    fetchShipments();
    fetchCarriers();
  }, [refreshTrigger]);
  
  // Handle tab change
  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };
  
  // Handle search input change
  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };
  
  // Handle status filter change
  const handleStatusFilterChange = (status) => {
    setStatusFilter(status);
  };
  
  // Handle carrier filter change
  const handleCarrierFilterChange = (carrier) => {
    setCarrierFilter(carrier);
  };
  
  // Handle delivery type filter change
  const handleDeliveryTypeFilterChange = (type) => {
    setDeliveryTypeFilter(type);
  };
  
  // Apply filters to shipments
  const filteredShipments = shipments.filter(shipment => {
    // Apply status filter
    if (statusFilter !== "All" && shipment.shipment_status !== statusFilter) {
      return false;
    }
    
    // Apply carrier filter (carrier_id or carrier_name)
    if (carrierFilter !== "All" && 
        shipment.carrier_id !== carrierFilter && 
        shipment.carrier_name !== carrierFilter) {
      return false;
    }
    
    // Apply delivery type filter (internal/external)
    if (deliveryTypeFilter !== "All" && shipment.delivery_type !== deliveryTypeFilter) {
      return false;
    }
    
    // Apply search filter (search by shipment_id, tracking_number, or delivery_id)
    if (searchTerm && 
        !shipment.shipment_id.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !shipment.tracking_number.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !String(shipment.delivery_id || '').toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    
    return true;
  });
  
  // Apply only search filter to failed shipments
  const filteredFailedShipments = failedShipments.filter(shipment => {
    // Apply search filter (search by shipment_id, tracking_number, or delivery_id)
    if (searchTerm && 
        !shipment.shipment_id.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !shipment.tracking_number.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !String(shipment.delivery_id || '').toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    
    return true;
  });
  
  // Handle shipment selection
  const handleShipmentSelect = (shipment) => {
    setSelectedShipment(shipment);
    setShowShipmentModal(true);
  };
  
  // Handle closing the shipment modal
  const handleCloseShipmentModal = () => {
    setShowShipmentModal(false);
  };
  
  // Handle save changes from the shipment modal
  const handleSaveChanges = async (shipment, updates) => {
    if (Object.keys(updates).length === 0) {
      setShowShipmentModal(false);
      return;
    }
    
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/shipments/${shipment.shipment_id}/update/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update shipment');
      }
      
      // Refresh the list after successful update
      setRefreshTrigger(prev => prev + 1);
      setShowShipmentModal(false);
      
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };
  
  // Handle ship status update
  const handleShipStatusUpdate = (shipment) => {
    setSelectedShipment(shipment);
    setShowShipmentModal(false);
    setShowConfirmShipModal(true);
  };
  
  // Handle confirming shipment
  const handleConfirmShipment = async () => {
    if (!selectedShipment) return;
    
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/shipments/${selectedShipment.shipment_id}/ship/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          shipment_status: 'Shipped'
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to mark shipment as shipped');
      }
      
      // Close modal and refresh the list
      setShowConfirmShipModal(false);
      setRefreshTrigger(prev => prev + 1);
      
      // Show success notification
      alert('Shipment marked as Shipped successfully! A delivery receipt has been created.');
      
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };
  
  // Handle showing delivery receipt modal
  const handleShowDeliveryReceipt = (shipment) => {
    setSelectedShipment(shipment);
    setShowShipmentModal(false);
    setShowDeliveryReceiptModal(true);
  };
  
  // Handle updating delivery receipt
  const handleUpdateDeliveryReceipt = async (deliveryReceipt) => {
    if (!selectedShipment) return;
    
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/delivery-receipts/${deliveryReceipt.delivery_receipt_id}/update/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(deliveryReceipt),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update delivery receipt');
      }
      
      // Close modal and refresh the list
      setShowDeliveryReceiptModal(false);
      setRefreshTrigger(prev => prev + 1);
      
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };
  
  // Handle report failure
  const handleReportFailure = (shipment) => {
    setSelectedShipment(shipment);
    setShowShipmentModal(false);
    setShowFailureReportModal(true);
  };
  
  // Handle submitting failure report
  const handleSubmitFailureReport = async (failureDetails) => {
    if (!selectedShipment) return;
    
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/shipments/${selectedShipment.shipment_id}/fail/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          shipment_status: 'Failed',
          failure_reason: failureDetails.failure_reason
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to report shipment failure');
      }
      
      // Close modal and refresh the list
      setShowFailureReportModal(false);
      setRefreshTrigger(prev => prev + 1);
      
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };
  
  // Refresh carriers
  const refreshCarriers = () => {
    setRefreshTrigger(prev => prev + 1);
  };
  
  // Calculate stats for the shipments tab
  const shipmentStats = {
    total: shipments.length,
    pending: shipments.filter(shipment => shipment.shipment_status === 'Pending').length,
    shipped: shipments.filter(shipment => shipment.shipment_status === 'Shipped').length,
    delivered: shipments.filter(shipment => shipment.shipment_status === 'Delivered').length
  };
  
  // Calculate stats for the failed shipments tab
  const failedStats = {
    total: failedShipments.length,
    pending: failedShipments.filter(shipment => 
      shipment.failed_shipment_info?.resolution_status === 'Pending').length,
    inProgress: failedShipments.filter(shipment => 
      shipment.failed_shipment_info?.resolution_status === 'In Progress').length,
    resolved: failedShipments.filter(shipment => 
      shipment.failed_shipment_info?.resolution_status === 'Resolved').length
  };
  
  return (
    <div className="shipment">
      <div className="body-content-container">
        <h2 className="page-title">Shipment Management</h2>
        
        {/* Tab Navigation */}
        <div className="tab-navigation">
          <div 
            className={`tab ${activeTab === "shipments" ? "active" : ""}`}
            onClick={() => handleTabChange("shipments")}
          >
            Active Shipments
          </div>
          <div 
            className={`tab ${activeTab === "failed" ? "active" : ""}`}
            onClick={() => handleTabChange("failed")}
          >
            Failed Shipments
          </div>
        </div>
        
        {/* Filters Row - slightly different for each tab */}
        <div className="filters-row">
          <div className="search-container">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              className="search-input"
              placeholder={activeTab === "shipments" 
                ? "Search by Shipment ID, Tracking #, or Delivery ID..." 
                : "Search failed shipments..."}
              value={searchTerm}
              onChange={handleSearchChange}
            />
          </div>
          
          {/* Only show these filters in the Shipments tab */}
          {activeTab === "shipments" && (
            <>
              <StatusFilter 
                selectedStatus={statusFilter}
                onStatusChange={handleStatusFilterChange}
              />
              
              <CarrierFilter 
                carriers={carriers}
                selectedCarrier={carrierFilter}
                onCarrierChange={handleCarrierFilterChange}
              />
              
              <DeliveryTypeFilter 
                selectedType={deliveryTypeFilter}
                onTypeChange={handleDeliveryTypeFilterChange}
              />
              
              <button 
                type="button" 
                className="save-button"
                onClick={() => setShowCarrierManagementModal(true)}
                style={{ marginLeft: 'auto' }}
              >
                Manage Carriers
              </button>
            </>
          )}
        </div>
        
        {/* Statistics Row - different stats for each tab */}
        <div className="stats-row">
          {activeTab === "shipments" ? (
            <>
              <div className="stat-box">
                <span className="stat-label">Total Shipments:</span>
                <span className="stat-value">{shipmentStats.total}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Pending:</span>
                <span className="stat-value">{shipmentStats.pending}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Shipped:</span>
                <span className="stat-value">{shipmentStats.shipped}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Delivered:</span>
                <span className="stat-value">{shipmentStats.delivered}</span>
              </div>
            </>
          ) : (
            <>
              <div className="stat-box">
                <span className="stat-label">Failed Shipments:</span>
                <span className="stat-value">{failedStats.total}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Pending Resolution:</span>
                <span className="stat-value">{failedStats.pending}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">In Progress:</span>
                <span className="stat-value">{failedStats.inProgress}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Resolved:</span>
                <span className="stat-value">{failedStats.resolved}</span>
              </div>
            </>
          )}
        </div>
        
        {/* Content based on active tab */}
        {loading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Loading shipments...</p>
          </div>
        ) : error ? (
          <div className="error-container">
            <p className="error-message">Error: {error}</p>
          </div>
        ) : (
          <div className="shipment-content">
            {activeTab === "shipments" ? (
              <ShipmentTable 
                shipments={filteredShipments} 
                onShipmentSelect={handleShipmentSelect} 
                selectedShipment={selectedShipment}
                carriers={carriers}
              />
            ) : (
              <FailedShipmentsTable 
                failedShipments={filteredFailedShipments}
                onShipmentSelect={handleShipmentSelect}
                selectedShipment={selectedShipment}
                carriers={carriers}
              />
            )}
          </div>
        )}
        
        {/* Modals - these stay the same */}
        {showShipmentModal && selectedShipment && (
          <ShipmentModal 
            shipment={selectedShipment}
            carriers={carriers}
            onClose={handleCloseShipmentModal}
            onSave={handleSaveChanges}
            onShip={handleShipStatusUpdate}
            onShowDeliveryReceipt={handleShowDeliveryReceipt}
            onReportFailure={handleReportFailure}
          />
        )}
        
        {showConfirmShipModal && selectedShipment && (
          <ConfirmShipModal 
            shipment={selectedShipment}
            onConfirm={handleConfirmShipment}
            onCancel={() => setShowConfirmShipModal(false)}
          />
        )}
        
        {showDeliveryReceiptModal && selectedShipment && (
          <DeliveryReceiptModal 
            shipment={selectedShipment}
            onSave={handleUpdateDeliveryReceipt}
            onCancel={() => setShowDeliveryReceiptModal(false)}
          />
        )}
        
        {showFailureReportModal && selectedShipment && (
          <FailureReportModal 
            shipment={selectedShipment}
            onSubmit={handleSubmitFailureReport}
            onCancel={() => setShowFailureReportModal(false)}
          />
        )}
        
        {showCarrierManagementModal && (
          <CarrierManagementModal 
            carriers={carriers}
            refreshCarriers={refreshCarriers}
            onClose={() => setShowCarrierManagementModal(false)}
          />
        )}
      </div>
    </div>
  );
};

export default Shipment;