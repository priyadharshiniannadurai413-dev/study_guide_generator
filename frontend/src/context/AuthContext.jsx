/**
 * src/context/AuthContext.jsx
 * Unified authentication context connecting Clerk with backend API client.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth as useClerkAuth, useUser as useClerkUser, useClerk } from '@clerk/clerk-react';
import {
  getStoredToken,
  setStoredToken,
  getStoredUserId,
  setStoredUserId,
  setTokenProvider,
} from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const { isLoaded, isSignedIn, getToken, signOut: clerkSignOut } = useClerkAuth();
  const { user: clerkUser } = useClerkUser();
  const { openSignIn, openSignUp } = useClerk();

  const [token, setTokenState] = useState(getStoredToken());
  const [userId, setUserIdState] = useState(getStoredUserId());
  const [isDevMode, setIsDevMode] = useState(!getStoredToken());
  const [userName, setUserName] = useState('University Scholar');

  // Register dynamic token provider with API client for fresh, non-expired tokens on every request
  useEffect(() => {
    if (isSignedIn) {
      setTokenProvider(async (skipCache = false) => {
        try {
          const fresh = await getToken(skipCache ? { skipCache: true } : undefined);
          if (fresh) {
            setStoredToken(fresh);
            setTokenState(fresh);
          }
          return fresh;
        } catch (err) {
          console.error('[AuthContext] Error getting fresh token from Clerk:', err);
          return null;
        }
      });
    } else {
      setTokenProvider(null);
    }
  }, [isSignedIn, getToken]);

  // Synchronize Clerk session token to API client whenever auth state changes
  const refreshClerkSession = useCallback(async () => {
    if (isSignedIn) {
      try {
        const sessionToken = await getToken();
        if (sessionToken) {
          setStoredToken(sessionToken);
          setTokenState(sessionToken);
          setIsDevMode(false);
        }
        if (clerkUser?.id) {
          setStoredUserId(clerkUser.id);
          setUserIdState(clerkUser.id);
        }
        const displayName =
          clerkUser?.fullName ||
          clerkUser?.firstName ||
          clerkUser?.primaryEmailAddress?.emailAddress ||
          'Scholar';
        setUserName(displayName);
      } catch (err) {
        console.error('[AuthContext] Error retrieving Clerk session token:', err);
      }
    } else if (isLoaded && !isSignedIn) {
      // If signed out and not using a custom manual dev token
      const currentStored = getStoredToken();
      if (!currentStored || currentStored.startsWith('ey')) {
        // Clear expired/old JWTs
        setStoredToken('dev_student_user');
        setTokenState('dev_student_user');
        setIsDevMode(true);
      }
      setUserName('Guest Student');
    }
  }, [isSignedIn, isLoaded, clerkUser, getToken]);

  useEffect(() => {
    if (isLoaded) {
      refreshClerkSession();
    }
  }, [isLoaded, isSignedIn, clerkUser, refreshClerkSession]);

  const updateToken = (newToken) => {
    setStoredToken(newToken);
    setTokenState(newToken);
    if (newToken) {
      setIsDevMode(false);
    }
  };

  const updateUserId = (newId) => {
    setStoredUserId(newId);
    setUserIdState(newId);
  };

  const toggleDevMode = (enabled) => {
    setIsDevMode(enabled);
    if (enabled) {
      setStoredToken('dev_student_user');
      setTokenState('dev_student_user');
    }
  };

  const signOut = async () => {
    if (isSignedIn) {
      await clerkSignOut();
    }
    setStoredToken('dev_student_user');
    setTokenState('dev_student_user');
    setIsDevMode(true);
    setUserName('Guest Student');
  };

  return (
    <AuthContext.Provider
      value={{
        isLoaded,
        isSignedIn,
        clerkUser,
        token,
        userId,
        userName,
        isDevMode,
        updateToken,
        updateUserId,
        setUserName,
        toggleDevMode,
        openSignIn,
        openSignUp,
        signOut,
        refreshClerkSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
