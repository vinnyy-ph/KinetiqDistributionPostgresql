import React, { useState, useEffect } from "react";
import "../styles/ExternalDelivery.css";

const BodyContent = () => {
    return (
        <div className="external-delivery">
            <div className="body-content-container">
                <p>Hello External Delivery SubModule!</p>
                <p>Fill this container with your elements, change the display if need be.</p>
                <p>If you're going to style with css, use your unique namespace '.cusrep' at the start.</p>
            </div>
        </div>

    );
};

export default BodyContent;
