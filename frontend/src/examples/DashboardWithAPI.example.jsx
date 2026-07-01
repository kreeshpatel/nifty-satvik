// Example: Dashboard Integration with Real API
// This shows how to update Dashboard.jsx to use real backend data

import React, { useState, useEffect } from 'react';
import { fetchOverview, fetchSignals, kiteLTP, kitePositions, kiteHoldings } from '@/services/api';
import useWebSocket from '@/hooks/useWebSocket';
import useKiteAuth from '@/hooks/useKiteAuth';

const DashboardWithAPI = () => {
  const [overview, setOverview] = useState(null);
  const [signals, setSignals] = useState([]);
  const [holdings, setHoldings] = useState([]);
  const [positions, setPositions] = useState([]);
  const [ltpData, setLtpData] = useState({});
  const [loading, setLoading] = useState(true);

  const { isLoggedIn, userId, handleCallback } = useKiteAuth();

  // WebSocket for live updates
  const { isConnected } = useWebSocket({
    onPortfolioUpdate: (data) => {
      setOverview(prev => ({ ...prev, ...data }));
    },
    onTick: (data) => {
      setLtpData(prev => ({ ...prev, ...data.ticks }));
    },
    onOrderUpdate: (data) => {
      loadPositions();
    },
  });

  // Load data
  useEffect(() => {
    const loadData = async () => {
      try {
        const [overviewData, signalsData, holdingsData, positionsData] = await Promise.all([
          fetchOverview(),
          fetchSignals(),
          isLoggedIn ? kiteHoldings() : [],
          isLoggedIn ? kitePositions() : { net: [] },
        ]);

        setOverview(overviewData);
        setSignals(signalsData);
        setHoldings(holdingsData);
        setPositions(positionsData.net || []);

        const tokens = [...holdingsData, ...positionsData.net]
          .map(h => h.instrument_token).filter(Boolean);
        
        if (tokens.length > 0) {
          const ltp = await kiteLTP(tokens);
          setLtpData(ltp);
        }
      } catch (error) {
        console.error('Load error:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [isLoggedIn]);

  const loadPositions = async () => {
    const data = await kitePositions();
    setPositions(data.net || []);
  };

  return (
    <div>
      {/* Use overview, signals, holdings, positions, ltpData */}
    </div>
  );
};

export default DashboardWithAPI;
