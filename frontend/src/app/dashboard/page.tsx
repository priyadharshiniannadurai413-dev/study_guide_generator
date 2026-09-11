import React from 'react';
import { DashboardPage } from '../../pages/DashboardPage';

export default function Page({ setActiveTab = () => {} }: { setActiveTab?: (tab: string) => void }) {
  return <DashboardPage setActiveTab={setActiveTab} />;
}
