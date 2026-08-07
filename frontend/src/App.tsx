import React from 'react';
import { useAppStore } from './store/useAppStore';
import { UploadScreen } from './components/UploadScreen';
import { MainLayout } from './components/MainLayout';

export const App: React.FC = () => {
  const { currentView } = useAppStore();

  if (currentView === 'upload') {
    return <UploadScreen />;
  }

  return <MainLayout />;
};

export default App;
