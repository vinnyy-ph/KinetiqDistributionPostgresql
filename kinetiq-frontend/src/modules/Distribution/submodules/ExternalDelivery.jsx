import React, { useState, useEffect } from "react";
import "../styles/ExternalDelivery.css";
import { Table, Spinner, Alert } from "react-bootstrap";

const BodyContent = () => {
    const [deliveryOrders, setDeliveryOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Fetch delivery orders from the Django backend
        const fetchDeliveryOrders = async () => {
            try {
                const response = await fetch('/api/delivery-orders/');
                if (!response.ok) {
                    throw new Error('Failed to fetch delivery orders');
                }
                const data = await response.json();
                setDeliveryOrders(data);
                setLoading(false);
            } catch (err) {
                setError(err.message);
                setLoading(false);
            }
        };

        fetchDeliveryOrders();
    }, []);

    if (loading) {
        return (
            <div className="external-delivery">
                <div className="body-content-container d-flex justify-content-center align-items-center">
                    <Spinner animation="border" role="status">
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
                <h2 className="mb-4">External Delivery Orders</h2>
                <Table striped bordered hover responsive>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Status</th>
                            <th>Type</th>
                            <th>Project Based</th>
                            <th>Partial Delivery</th>
                            <th>Sales Order ID</th>
                            <th>Service Order ID</th>
                            <th>Stock Transfer ID</th>
                            <th>Content ID</th>
                        </tr>
                    </thead>
                    <tbody>
                        {deliveryOrders.length > 0 ? (
                            deliveryOrders.filter(order => order.del_type === 'External Delivery')
                                .map(order => (
                                    <tr key={order.del_order_id}>
                                        <td>{order.del_order_id}</td>
                                        <td>{order.order_status}</td>
                                        <td>{order.del_type}</td>
                                        <td>{order.is_project_based}</td>
                                        <td>{order.is_partial_delivery}</td>
                                        <td>{order.sales_order_id || '-'}</td>
                                        <td>{order.service_order_id || '-'}</td>
                                        <td>{order.stock_transfer_id || '-'}</td>
                                        <td>{order.content_id || '-'}</td>
                                    </tr>
                                ))
                        ) : (
                            <tr>
                                <td colSpan="9" className="text-center">No external delivery orders found</td>
                            </tr>
                        )}
                    </tbody>
                </Table>
            </div>
        </div>
    );
};

export default BodyContent;