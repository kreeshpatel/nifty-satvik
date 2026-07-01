import { useEffect, useRef, useCallback, useState } from 'react';
import { initWebSocket, subscribeToTicks, unsubscribeFromTicks, closeWebSocket } from '@/services/api';

/**
 * Custom hook for WebSocket real-time updates
 * @param {Object} callbacks - { onPortfolioUpdate, onTick, onOrderUpdate }
 * @param {Array<number>} tokens - Instrument tokens to subscribe to
 * @returns {Object} { isConnected, subscribe, unsubscribe }
 */
export const useWebSocket = (callbacks = {}, tokens = []) => {
  const wsRef = useRef(null);
  // Ref drives the imperative subscribe/unsubscribe guards (read inside
  // callbacks); state drives the returned `isConnected` so consumers actually
  // re-render when the connection flips (a bare ref read never re-renders).
  const isConnectedRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // BUG FIX: initWebSocket is async (it fetches a WS ticket first), so it
    // returns a Promise — NOT the socket. The previous code did
    // `wsRef.current = initWebSocket(...)` then set `.onopen` on that Promise,
    // which was a no-op: isConnectedRef never flipped true, so the hook's
    // subscribe/unsubscribe (guarded on it) and the initial token auto-subscribe
    // never ran — live tick subscriptions were dead. (Server-pushed portfolio/
    // order updates still worked because initWebSocket wires ws.onmessage
    // internally.) Await the real socket, then wire open/close via
    // addEventListener so we don't clobber initWebSocket's own handlers.
    let cancelled = false;
    (async () => {
      const socket = await initWebSocket(callbacks);
      if (cancelled || !socket) return;
      wsRef.current = socket;

      const markOpen = () => {
        isConnectedRef.current = true;
        setIsConnected(true);
        // Auto-subscribe to initial tokens once the socket is open.
        if (tokens.length > 0) {
          subscribeToTicks(tokens);
        }
      };
      if (socket.readyState === WebSocket.OPEN) {
        markOpen();
      } else {
        socket.addEventListener('open', markOpen);
      }
      socket.addEventListener('close', () => {
        isConnectedRef.current = false;
        setIsConnected(false);
      });
    })();

    // Cleanup on unmount
    return () => {
      cancelled = true;
      if (tokens.length > 0) {
        unsubscribeFromTicks(tokens);
      }
      closeWebSocket();
      isConnectedRef.current = false;
    };
    // Intentional: callbacks are captured at mount (services/api.js stores
    // them in a module-level wsCallbacks). Re-running this effect on every
    // callbacks/tokens change would close + reopen the socket on each render
    // and break the singleton invariant. Consumers should memoize callbacks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const subscribe = useCallback((newTokens) => {
    if (isConnectedRef.current) {
      subscribeToTicks(newTokens);
    }
  }, []);

  const unsubscribe = useCallback((tokensToRemove) => {
    if (isConnectedRef.current) {
      unsubscribeFromTicks(tokensToRemove);
    }
  }, []);

  return {
    isConnected,
    subscribe,
    unsubscribe,
  };
};

export default useWebSocket;
