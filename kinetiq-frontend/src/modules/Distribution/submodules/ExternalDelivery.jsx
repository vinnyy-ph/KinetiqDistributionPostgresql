import React, { useState, useEffect } from "react";
import "../styles/ExternalDelivery.css";
import { Table, Spinner, Alert, Form } from "react-bootstrap";

const ExternalDelivery = () => {
  const [deliveryOrders, setDeliveryOrders] = useState([]);
  const [filteredOrders, setFilteredOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [sortField, setSortField] = useState("del_order_id");
  const [sortDirection, setSortDirection] = useState("asc");

  useEffect(() => {
    // Fetch delivery orders from the backend
    const fetchDeliveryOrders = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/delivery-orders/');
        if (!response.ok) {
          throw new Error('Failed to fetch delivery orders');
        }
        const data = await response.json();
        // Filter for external delivery orders only
        const externalOrders = data.filter(order => order.del_type === 'External Delivery');
        setDeliveryOrders(externalOrders);
        setFilteredOrders(externalOrders);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchDeliveryOrders();
  }, []);
  
  useEffect(() => {
    // Apply filters and search whenever they change
    let result = [...deliveryOrders];
    
    // Apply status filter if not "All"
    if (statusFilter !== "All") {
      result = result.filter(order => order.order_status === statusFilter);
    }
    
    // Apply search filter across multiple fields
    if (searchTerm.trim() !== "") {
      const term = searchTerm.toLowerCase();
      result = result.filter(order => 
        String(order.del_order_id || "").toLowerCase().includes(term) ||
        String(order.sales_order_id || "").toLowerCase().includes(term) ||
        String(order.service_order_id || "").toLowerCase().includes(term) ||
        String(order.stock_transfer_id || "").toLowerCase().includes(term)
      );
    }
    
    // Apply sorting
    result.sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];
      
      // Handle null values for sorting
      if (aValue === null || aValue === undefined) aValue = '';
      if (bValue === null || bValue === undefined) bValue = '';
      
      // Convert to strings for consistent comparison
      aValue = String(aValue).toLowerCase();
      bValue = String(bValue).toLowerCase();
      
      if (sortDirection === "asc") {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
    
    setFilteredOrders(result);
  }, [deliveryOrders, searchTerm, statusFilter, sortField, sortDirection]);
  
  // Handle column sorting
  const handleSort = (field) => {
    const newDirection = field === sortField && sortDirection === "asc" ? "desc" : "asc";
    setSortField(field);
    setSortDirection(newDirection);
  };
  
  // Pagination logic
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredOrders.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(filteredOrders.length / itemsPerPage);
  
  // Format ID for display (based on the screenshot pattern)
  const formatOrderId = (id) => {
    if (!id) return "-";
    // Convert standard ID to the DIS-DO-YYYY-XXXXX format if needed
    if (id.startsWith("DIS-DO-")) return id;
    return `DIS-DO-${new Date().getFullYear()}-${id}`;
  };
  
  // Format Sales Order ID
  const formatSalesId = (id) => {
    if (!id) return "-";
    if (id.startsWith("SALES-ORD-")) return id;
    return `SALES-ORD-${new Date().getFullYear()}-${id}`;
  };
  
  // Format Service Order ID
  const formatServiceId = (id) => {
    if (!id) return "-";
    if (id.startsWith("SERVICES-DO-")) return id;
    return `SERVICES-DO-${new Date().getFullYear()}-${id}`;
  };

  if (loading) {
    return (
      <div className="external-delivery">
        <div className="body-content-container d-flex justify-content-center align-items-center">
          <Spinner animation="border" role="status" className="text-secondary">
            <span className="visually-hidden">Loading...</span>
          </Spinner>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="external-delivery">
        <div className="body-content-container">
          <Alert variant="danger">
            Error: {error}
          </Alert>
        </div>
      </div>
    );
  }

  return (
    <div className="external-delivery">
      <div className="body-content-container">
        <h2 className="page-title">External Delivery Orders</h2>
        <div className="order-count">Showing {filteredOrders.length} of {deliveryOrders.length} orders</div>
        
        {/* Search and filter section */}
        <div className="filters-row">
          <div className="search-container">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              className="search-input"
              placeholder="Search by order ID, sales ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <div className="filter-container">
            <span className="filter-label">=</span>
            <Form.Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="status-filter"
            >
              <option value="All">All</option>
              <option value="Created">Created</option>
              <option value="Processing">Processing</option>
              <option value="Delivered">Delivered</option>
              <option value="Cancelled">Cancelled</option>
            </Form.Select>
          </div>
        </div>
        
        <div className="pagination-info">
          Page {currentPage} of {totalPages || 1}
        </div>
        
        {/* Table section */}
        <div className="table-container">
          <Table hover className="orders-table">
            <thead>
              <tr>
                <th className="sort-header" onClick={() => handleSort("del_order_id")}>
                  ID {sortField === "del_order_id" && (
                    <span className="sort-indicator">{sortDirection === "asc" ? "↑" : "↓"}</span>
                  )}
                </th>
                <th>Status</th>
                <th>Project Based</th>
                <th>Partial Delivery</th>
                <th>Sales Order ID</th>
                <th>Service Order ID</th>
                <th>Stock Transfer ID</th>
                <th>Content ID</th>
              </tr>
            </thead>
            <tbody>
              {currentItems.length > 0 ? (
                currentItems.map((order, index) => (
                  <tr key={order.del_order_id} className={index % 2 === 0 ? "even-row" : "odd-row"}>
                    <td className="order-id">{formatOrderId(order.del_order_id)}</td>
                    <td className="status">{order.order_status || "Created"}</td>
                    <td>{order.is_project_based ? "Yes" : "No"}</td>
                    <td>{order.is_partial_delivery ? "Yes" : "No"}</td>
                    <td>{formatSalesId(order.sales_order_id)}</td>
                    <td>{formatServiceId(order.service_order_id)}</td>
                    <td>{order.stock_transfer_id || "-"}</td>
                    <td>{order.content_id || "-"}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="8" className="no-data">No external delivery orders found</td>
                </tr>
              )}
            </tbody>
          </Table>
        </div>
        
        {/* Pagination controls */}
        {totalPages > 1 && (
          <div className="pagination-controls">
            <button
              className="pagination-button"
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
            >
              Previous
            </button>
            <span className="page-numbers">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pageNumber = currentPage > 3 && totalPages > 5 ? 
                  currentPage - 2 + i : i + 1;
                
                if (pageNumber <= totalPages) {
                  return (
                    <button
                      key={pageNumber}
                      className={`page-number ${currentPage === pageNumber ? "active" : ""}`}
                      onClick={() => setCurrentPage(pageNumber)}
                    >
                      {pageNumber}
                    </button>
                  );
                }
                return null;
              })}
            </span>
            <button
              className="pagination-button"
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExternalDelivery;