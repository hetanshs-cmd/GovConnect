import React, { useState } from 'react';
import UserManagement from '../components/UserManagement';
import ServiceManagement from '../components/ServiceManagement';
import DynamicDatabase from '../components/DynamicDatabase';
import PageManagement from '../components/PageManagement';
import Makesections from '../components/Makesections';

interface AdminPageProps {
	isDark: boolean;
	user: any;
}

const AdminPage: React.FC<AdminPageProps> = ({ isDark, user }) => {
	const [activeTab, setActiveTab] = useState<'users' | 'services' | 'sections' | 'database' | 'pages'>('users');

	// Only show for admin and super_admin users
	if (!user || (user.role !== 'admin' && user.role !== 'super_admin')) {
		return (
			<div className="flex items-center justify-center py-8">
				<div className="text-center">
					<h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-black'}`}>Access Denied</h2>
					<p className={`text-sm mt-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
						You don't have permission to access this page.
					</p>
				</div>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			{/* Tab Navigation */}
			<div className="flex border-b border-gray-200 dark:border-gray-700">
				<button
					onClick={() => setActiveTab('users')}
					className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${activeTab === 'users'
						? 'border-blue-500 text-blue-600 dark:text-blue-400'
						: `border-transparent ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`
						}`}
				>
					User Management
				</button>
				<button
					onClick={() => setActiveTab('services')}
					className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${activeTab === 'services'
						? 'border-blue-500 text-blue-600 dark:text-blue-400'
						: `border-transparent ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`
						}`}
				>
					Service Management
				</button>
				<button
					onClick={() => setActiveTab('sections')}
					className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${activeTab === 'sections'
						? 'border-blue-500 text-blue-600 dark:text-blue-400'
						: `border-transparent ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`
						}`}
				>
					Section Management
				</button>
				<button
					onClick={() => setActiveTab('database')}
					className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${activeTab === 'database'
						? 'border-blue-500 text-blue-600 dark:text-blue-400'
						: `border-transparent ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`
						}`}
				>
					Dynamic Database
				</button>
				{user.role === 'super_admin' && (
					<button
						onClick={() => setActiveTab('pages')}
						className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${activeTab === 'pages'
							? 'border-blue-500 text-blue-600 dark:text-blue-400'
							: `border-transparent ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`
							}`}
					>
						Page Management
					</button>
				)}
			</div>

			{/* Tab Content */}
			{activeTab === 'users' && <UserManagement isDark={isDark} user={user} />}
			{activeTab === 'services' && <ServiceManagement isDark={isDark} user={user} />}
			{activeTab === 'sections' && <Makesections isDark={isDark} />}
			{activeTab === 'database' && <DynamicDatabase isDark={isDark} user={user} />}
			{activeTab === 'pages' && user.role === 'super_admin' && <PageManagement isDark={isDark} user={user} />}
		</div>
	);
};

export default AdminPage;