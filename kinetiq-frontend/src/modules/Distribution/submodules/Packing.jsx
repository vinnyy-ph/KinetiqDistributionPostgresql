import React, { useState, useEffect } from "react";
import "../styles/Packing.css";

const BodyContent = () => {
    return (
        <div className="packing">
            <div className="body-content-container">
                <p>Hello Packing SubModule!</p>
                <p>Fill this container with your elements, change the display if need be.</p>
                <p>If you're going to style with css, use your unique namespace '.packing' at the start.</p>
            </div>
        </div>

    );
};

export default BodyContent;
