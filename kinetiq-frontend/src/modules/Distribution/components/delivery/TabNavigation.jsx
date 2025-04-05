import React from "react";

const TabNavigation = ({ activeTab, onTabChange }) => {
  return (
    <div className="tab-navigation">
      <div 
        className={`tab ${activeTab === 'sales' ? 'active' : ''}`}
        onClick={() => onTabChange('sales')}
      >
        Sales Delivery
      </div>
      <div 
        className={`tab ${activeTab === 'service' ? 'active' : ''}`}
        onClick={() => onTabChange('service')}
      >
        Service Delivery
      </div>
    </div>
  );
};

export default TabNavigation;