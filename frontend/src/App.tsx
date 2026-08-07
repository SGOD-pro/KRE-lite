import React from 'react';
import { useAppStore } from './store/useAppStore';
import { UploadScreen } from './components/UploadScreen';
import { MainLayout } from './components/MainLayout';

export const App: React.FC = () => {
  const { currentView, sessionId } = useAppStore();

  // If there is no active session_id, always show the upload screen
  if (!sessionId || currentView === 'upload') {
    return <UploadScreen />;
  }

  return <MainLayout />;
};

export default App;
