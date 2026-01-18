import React from 'react';
import Dashboard from '../components/Dashboard';

interface HomePageProps {
  isDark: boolean;
  user?: { username: string; role: string } | null;
}

const HomePage: React.FC<HomePageProps> = ({ isDark, user }) => {
  return <Dashboard isDark={isDark} user={user} />;
};

export default HomePage;