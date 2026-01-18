import React from 'react';
import Dashboard from '../components/Dashboard';

interface CustomDashboardPageProps {
	isDark: boolean;
	user?: any;
}

const CustomDashboardPage: React.FC<CustomDashboardPageProps> = ({ isDark, user }) => {
	// Only allow superadmin to access this page
	if (!user || user.role !== 'super_admin') {
		return (
			<div className={`p-6 ${isDark ? 'text-white' : 'text-black'}`}>
				<h2 className="text-2xl font-bold mb-4">Access Denied</h2>
				<p>Only super administrators can access this page.</p>
			</div>
		);
	}

	return <Dashboard isDark={isDark} isCustom={true} />;
};

export default CustomDashboardPage;