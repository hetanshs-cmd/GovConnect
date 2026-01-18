
import React, { useState, useEffect } from 'react';
import KPICard from './KPICard';
import AlertFeed from './AlertFeed';
import { Users, Server, Map, Activity, Clock, AlertTriangle, Plus, X, Save, LayoutDashboard, Trash2 } from 'lucide-react';

interface DashboardProps {
  isDark?: boolean;
  isCustom?: boolean;
  customTitle?: string;
  customDescription?: string;
  pageId?: number;
  user?: { username: string; role: string } | null;
}

interface DynamicSection {
  id: string;
  title: string;
  type: 'form' | 'data' | 'chart' | 'full_section';
  table_name?: string;
  fields?: Array<{
    name: string;
    type: string;
    required: boolean;
    show_ui?: boolean;
  }>;
  icon?: string;
  description?: string;
}

interface DynamicFormSectionProps {
  tableName: string;
  fields: Array<{
    name: string;
    type: string;
    required: boolean;
    show_ui?: boolean;
  }>;
  isDark: boolean;
}

const DynamicFormSection: React.FC<DynamicFormSectionProps> = ({ tableName, fields, isDark }) => {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Load existing submissions
  useEffect(() => {
    loadSubmissions();
  }, [tableName]);

  const loadSubmissions = async () => {
    try {
      const response = await fetch(`/api/admin/dynamic/tables/${tableName}/data`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setSubmissions(data.data || []);
      }
    } catch (error) {
      console.error('Error loading submissions:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch(`/api/admin/dynamic/tables/${tableName}/data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        setFormData({});
        loadSubmissions();
      }
    } catch (error) {
      console.error('Error submitting form:', error);
    }

    setLoading(false);
  };

  const handleInputChange = (fieldName: string, value: any) => {
    setFormData({ ...formData, [fieldName]: value });
  };

  return (
    <div className="space-y-4">
      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {fields.filter(field => field.show_ui !== false).map((field) => (
            <div key={field.name}>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                {field.name} {field.required && <span className="text-red-500">*</span>}
              </label>

              {field.type === 'bool' ? (
                <input
                  type="checkbox"
                  checked={formData[field.name] || false}
                  onChange={(e) => handleInputChange(field.name, e.target.checked)}
                  className="w-4 h-4"
                />
              ) : (
                <input
                  type={field.type === 'int' || field.type === 'float' ? 'number' :
                    field.type === 'date' ? 'date' : 'text'}
                  value={formData[field.name] || ''}
                  onChange={(e) => handleInputChange(field.name, e.target.value)}
                  required={field.required}
                  step={field.type === 'float' ? '0.01' : undefined}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${isDark
                    ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                    : 'bg-white border-gray-300 text-black placeholder-gray-500'
                    }`}
                />
              )}
            </div>
          ))}
        </div>

        <button
          type="submit"
          disabled={loading}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${isDark
            ? 'bg-green-600 hover:bg-green-700 text-white disabled:bg-green-800'
            : 'bg-green-500 hover:bg-green-600 text-white disabled:bg-green-400'
            }`}
        >
          {loading ? 'Submitting...' : 'Submit'}
        </button>
      </form>

      {/* Submissions */}
      {submissions.length > 0 && (
        <div>
          <h4 className={`text-md font-semibold mb-2 ${isDark ? 'text-white' : 'text-black'}`}>
            Recent Submissions ({submissions.length})
          </h4>
          <div className={`max-h-40 overflow-y-auto border rounded ${isDark ? 'border-gray-600' : 'border-gray-300'
            }`}>
            <table className="w-full text-sm">
              <thead className={isDark ? 'bg-gray-700' : 'bg-gray-50'}>
                <tr>
                  {Object.keys(submissions[0] || {}).map((key) => (
                    <th key={key} className={`px-3 py-2 text-left font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'
                      }`}>
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {submissions.slice(0, 5).map((submission, index) => (
                  <tr key={index} className={isDark ? 'border-t border-gray-600' : 'border-t border-gray-200'}>
                    {Object.values(submission).map((value: any, i) => (
                      <td key={i} className={`px-3 py-2 ${isDark ? 'text-gray-300' : 'text-gray-700'
                        }`}>
                        {String(value)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

const Dashboard: React.FC<DashboardProps> = ({ isDark = true, isCustom = false, customTitle, customDescription, pageId, user }) => {
  const [showAddSection, setShowAddSection] = useState(false);
  const [dynamicSections, setDynamicSections] = useState<DynamicSection[]>([]);
  const [newSection, setNewSection] = useState({
    title: '',
    type: 'form' as 'form' | 'data' | 'chart' | 'full_section',
    table_name: '',
    icon: 'Database',
    description: '',
    fields: [{ name: '', type: 'string', required: false, show_ui: true }]
  });

  // KPI Statistics State
  const [kpiStats, setKpiStats] = useState({
    totalUsers: 'Loading...',
    activeServices: 'Loading...',
    regions: 'Loading...',
    alertsToday: 'Loading...',
    requestsPerMinute: 'Loading...'
  });

  // Load dynamic sections from localStorage (in a real app, this would come from an API)
  useEffect(() => {
    const storageKey = pageId ? `page_${pageId}_sections` : (isCustom ? 'custom_dashboard_sections' : 'dynamic_sections');
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      setDynamicSections(JSON.parse(saved));
    }
    loadKPIStats();
  }, [isCustom, pageId]);

  // Load KPI statistics from API
  const loadKPIStats = async () => {
    try {
      const [usersRes, servicesRes, regionsRes, alertsRes, requestsRes] = await Promise.all([
        fetch('/api/dashboard/stats/users', { credentials: 'include' }),
        fetch('/api/dashboard/stats/services', { credentials: 'include' }),
        fetch('/api/dashboard/stats/regions', { credentials: 'include' }),
        fetch('/api/dashboard/stats/alerts-today', { credentials: 'include' }),
        fetch('/api/dashboard/stats/requests-per-minute', { credentials: 'include' })
      ]);

      const users = usersRes.ok ? await usersRes.json() : { total_users: 'Error' };
      const services = servicesRes.ok ? await servicesRes.json() : { active_services: 'Error' };
      const regions = regionsRes.ok ? await regionsRes.json() : { regions: 'Error' };
      const alerts = alertsRes.ok ? await alertsRes.json() : { alerts_today: 'Error' };
      const requests = requestsRes.ok ? await requestsRes.json() : { requests_per_minute: 'Error' };

      setKpiStats({
        totalUsers: users.total_users?.toString() || 'Error',
        activeServices: services.active_services?.toString() || 'Error',
        regions: regions.regions?.toString() || 'Error',
        alertsToday: alerts.alerts_today?.toString() || 'Error',
        requestsPerMinute: requests.requests_per_minute?.toString() || 'Error'
      });
    } catch (error) {
      console.error('Error loading KPI stats:', error);
      setKpiStats({
        totalUsers: 'Error',
        activeServices: 'Error',
        regions: 'Error',
        alertsToday: 'Error',
        requestsPerMinute: 'Error'
      });
    }
  };

  // Save dynamic sections to localStorage
  const saveSections = (sections: DynamicSection[]) => {
    const storageKey = pageId ? `page_${pageId}_sections` : (isCustom ? 'custom_dashboard_sections' : 'dynamic_sections');
    localStorage.setItem(storageKey, JSON.stringify(sections));
    setDynamicSections(sections);
  };

  // Delete section and associated database table (for superadmin only)
  const deleteSection = async (section: DynamicSection) => {
    if (user?.role !== 'super_admin') return;

    // Confirm deletion
    if (!confirm(`Are you sure you want to delete the "${section.title}" section? This will permanently delete all associated data.`)) {
      return;
    }

    try {
      // If it's a form section with a table, delete the database table
      if (section.type === 'form' && section.table_name) {
        const response = await fetch(`/api/admin/dynamic/tables/${section.table_name}`, {
          method: 'DELETE',
          credentials: 'include',
        });

        if (!response.ok) {
          console.warn('Failed to delete database table:', section.table_name);
        }

        // Also try to delete associated service if it exists
        try {
          // First get all services to find the one with matching name
          const servicesResponse = await fetch('/api/admin/services', {
            credentials: 'include',
          });

          if (servicesResponse.ok) {
            const services = await servicesResponse.json();
            const serviceToDelete = services.find((s: any) => s.name === section.table_name);

            if (serviceToDelete) {
              const serviceDeleteResponse = await fetch(`/api/admin/services/${serviceToDelete.id}`, {
                method: 'DELETE',
                credentials: 'include',
              });
              if (!serviceDeleteResponse.ok) {
                console.warn('Failed to delete associated service');
              }
            }
          }
        } catch (err) {
          console.warn('Error deleting associated service:', err);
        }
      }

      // Remove from localStorage
      const updatedSections = dynamicSections.filter(s => s.id !== section.id);
      saveSections(updatedSections);

      console.log(`Section "${section.title}" deleted successfully`);
    } catch (error) {
      console.error('Error deleting section:', error);
      alert('Failed to delete section. Please try again.');
    }
  };

  const addField = () => {
    setNewSection({
      ...newSection,
      fields: [...newSection.fields, { name: '', type: 'string', required: false, show_ui: true }]
    });
  };

  const updateField = (index: number, key: string, value: any) => {
    const updatedFields = [...newSection.fields];
    updatedFields[index] = { ...updatedFields[index], [key]: value };
    setNewSection({ ...newSection, fields: updatedFields });
  };

  const removeField = (index: number) => {
    if (newSection.fields.length > 1) {
      setNewSection({
        ...newSection,
        fields: newSection.fields.filter((_, i) => i !== index)
      });
    }
  };

  const createSection = async () => {
    if (!newSection.title.trim()) return;

    // Create dynamic table for full sections
    if ((newSection.type === 'form' || newSection.type === 'full_section') && newSection.fields.some(f => f.name.trim())) {
      try {
        const tableName = `user_section_${Date.now()}`;
        const validFields = newSection.fields.filter(f => f.name.trim());

        const response = await fetch('/api/admin/dynamic/tables', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            table_name: tableName,
            fields: validFields.map(f => f.name),
            data_types: validFields.map(f => f.type),
            show_ui: validFields.map(f => f.show_ui)
          })
        });

        if (response.ok) {
          const section: DynamicSection = {
            id: Date.now().toString(),
            title: newSection.title,
            type: newSection.type,
            table_name: tableName,
            fields: validFields,
            icon: newSection.icon,
            description: newSection.description
          };

          // Persist frontend state
          saveSections([...dynamicSections, section]);

          // Register as a service so navigation and backend know about this section
          try {
            const serviceResp = await fetch('/api/admin/services', {
              method: 'POST',
              credentials: 'include',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                name: tableName,
                displayName: newSection.title,
                route: `/${newSection.title.toLowerCase().replace(/\s+/g, '-')}`,
                componentName: 'DynamicFullSection',
                icon: newSection.icon,
                description: newSection.description,
                isActive: true
              })
            });

            if (!serviceResp.ok) {
              console.warn('Failed to register service for dynamic section');
            }
          } catch (err) {
            console.warn('Error registering dynamic section service:', err);
          }

          // If it's a full section, also register it for navigation
          if (newSection.type === 'full_section') {
            const existingSections = JSON.parse(localStorage.getItem('dynamic_full_sections') || '[]');
            const fullSectionData = {
              id: section.id,
              title: section.title,
              path: `/${section.title.toLowerCase().replace(/\s+/g, '-')}`,
              icon: section.icon,
              table_name: tableName,
              fields: validFields,
              description: section.description
            };
            localStorage.setItem('dynamic_full_sections', JSON.stringify([...existingSections, fullSectionData]));
          }

          setNewSection({
            title: '',
            type: 'form',
            table_name: '',
            icon: 'Database',
            description: '',
            fields: [{ name: '', type: 'string', required: false, show_ui: true }]
          });
          setShowAddSection(false);
        }
      } catch (error) {
        console.error('Error creating dynamic table:', error);
      }
    } else {
      // For non-form sections
      const section: DynamicSection = {
        id: Date.now().toString(),
        title: newSection.title,
        type: newSection.type,
        icon: newSection.icon,
        description: newSection.description
      };

      saveSections([...dynamicSections, section]);
      setNewSection({
        title: '',
        type: 'form',
        table_name: '',
        icon: 'Database',
        description: '',
        fields: [{ name: '', type: 'string', required: false, show_ui: true }]
      });
      setShowAddSection(false);
    }
  };

  const removeSection = (id: string) => {
    const updatedSections = dynamicSections.filter(s => s.id !== id);
    saveSections(updatedSections);
  };
  return (
    <div className="space-y-4">
      {/* Header with Add Section Button */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-black'}`}>
            {customTitle || (isCustom ? 'Custom Dashboard' : 'Dashboard')}
          </h2>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {customDescription || (isCustom ? 'Your personalized dashboard with custom sections' : 'System overview and management dashboard')}
          </p>
        </div>
        {(() => {
          console.log('User role check:', user?.role, 'isCustom:', isCustom);
          // Only show Add Field/Section button to superadmin
          const shouldShow = user?.role === 'super_admin';
          return shouldShow && (
            <div className="text-right">
              <button
                onClick={() => setShowAddSection(true)}
                className={`flex items-center px-6 py-3 rounded-lg font-medium transition-colors border-2 ${isDark
                  ? 'bg-blue-600 hover:bg-blue-700 text-white border-blue-500'
                  : 'bg-blue-500 hover:bg-blue-600 text-white border-blue-400'
                  }`}
              >
                <Plus className="w-5 h-5 mr-2" />
                Add Field/Section
              </button>
              <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Add custom fields and sections to the dashboard (Super Admin Only)
              </p>
            </div>
          );
        })()}
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KPICard title="Total Users" value={kpiStats.totalUsers} trend="+2.4%" icon={Users} color="indigo" isDark={isDark} />
        <KPICard title="Active Services" value={kpiStats.activeServices} trend="stable" icon={Server} color="blue" isDark={isDark} />
        <KPICard title="Regions" value={kpiStats.regions} trend="100%" icon={Map} color="emerald" isDark={isDark} />
        <KPICard title="System Uptime" value="99.98%" trend="+0.01%" icon={Activity} color="cyan" isDark={isDark} />
        <KPICard title="Requests per Minute" value={kpiStats.requestsPerMinute} trend="+12%" icon={Clock} color="purple" isDark={isDark} />
        <KPICard title="Alerts Today" value={kpiStats.alertsToday} trend="-4" icon={AlertTriangle} color="rose" isDark={isDark} />
      </div>

      {/* Dynamic Sections */}
      {dynamicSections.map((section) => (
        <div key={section.id} className={`p-6 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
          <div className="flex justify-between items-center mb-4">
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-black'}`}>
              {section.title}
            </h3>
            {/* Only show delete buttons for superadmin */}
            {user?.role === 'super_admin' && (
              <div className="flex gap-1">
                <button
                  onClick={() => removeSection(section.id)}
                  className={`p-1 rounded transition-colors ${isDark ? 'hover:bg-gray-700 text-gray-400' : 'hover:bg-gray-100 text-gray-600'
                    }`}
                  title="Remove from view"
                >
                  <X className="w-4 h-4" />
                </button>
                <button
                  onClick={() => deleteSection(section)}
                  className={`p-1 rounded transition-colors ${isDark ? 'hover:bg-red-700 text-red-400' : 'hover:bg-red-100 text-red-600'
                    }`}
                  title="Permanently delete section and data"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {section.type === 'form' && section.table_name && (
            <DynamicFormSection
              tableName={section.table_name}
              fields={section.fields || []}
              isDark={isDark}
            />
          )}

          {section.type === 'data' && (
            <div className={`p-4 rounded ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
              <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                Data visualization section - Coming soon!
              </p>
            </div>
          )}

          {section.type === 'chart' && (
            <div className={`p-4 rounded ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
              <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                Chart section - Coming soon!
              </p>
            </div>
          )}
        </div>
      ))}

      {/* Custom Dashboard Management - Super Admin Only */}
      {!isCustom && user?.role === 'super_admin' && (
        <div className={`p-6 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
          <div className="flex justify-between items-center mb-4">
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-black'}`}>
              Custom Dashboard Management
            </h3>
            <button
              onClick={() => window.open('/custom-dashboard', '_blank')}
              className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${isDark
                ? 'bg-purple-600 hover:bg-purple-700 text-white'
                : 'bg-purple-500 hover:bg-purple-600 text-white'
                }`}
            >
              <LayoutDashboard className="w-4 h-4 mr-2" />
              Open Custom Dashboard
            </button>
          </div>
          <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'} mb-4`}>
            Manage your custom dashboard with personalized sections, KPIs, and data visualizations.
            The custom dashboard replicates all dashboard functionality with full customization capabilities.
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => window.open('/custom-dashboard', '_blank')}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isDark
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-blue-500 hover:bg-blue-600 text-white'
                }`}
            >
              Configure Dashboard
            </button>
            <button
              onClick={() => {
                const customSections = JSON.parse(localStorage.getItem('custom_dashboard_sections') || '[]');
                alert(`Custom Dashboard has ${customSections.length} sections configured.`);
              }}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isDark
                ? 'bg-gray-600 hover:bg-gray-700 text-white'
                : 'bg-gray-500 hover:bg-gray-600 text-white'
                }`}
            >
              View Statistics
            </button>
          </div>
        </div>
      )}

      {/* Alert Feed */}
      <div className="w-full">
        <AlertFeed isDark={isDark} />
      </div>

      {/* Add Section Modal */}
      {showAddSection && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className={`p-6 rounded-lg w-full max-w-md ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="flex justify-between items-center mb-4">
              <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-black'}`}>
                Add New Section
              </h3>
              <button
                onClick={() => setShowAddSection(false)}
                className={`p-1 rounded transition-colors ${isDark ? 'hover:bg-gray-700 text-gray-400' : 'hover:bg-gray-100 text-gray-600'
                  }`}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Section Title */}
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  Section Title
                </label>
                <input
                  type="text"
                  value={newSection.title}
                  onChange={(e) => setNewSection({ ...newSection, title: e.target.value })}
                  placeholder="Enter section title"
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${isDark
                    ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                    : 'bg-white border-gray-300 text-black placeholder-gray-500'
                    }`}
                />
              </div>

              {/* Section Type */}
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  Section Type
                </label>
                <select
                  value={newSection.type}
                  onChange={(e) => setNewSection({ ...newSection, type: e.target.value as 'form' | 'data' | 'chart' | 'full_section' })}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${isDark
                    ? 'bg-gray-700 border-gray-600 text-white'
                    : 'bg-white border-gray-300 text-black'
                    }`}
                >
                  <option value="form">Data Collection Form</option>
                  <option value="full_section">Full Section (with dedicated page)</option>
                  <option value="data">Data Display</option>
                  <option value="chart">Chart/Visualization</option>
                </select>
              </div>

              {/* Icon Selection (for full sections) */}
              {(newSection.type === 'full_section' || newSection.type === 'form') && (
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Icon
                  </label>
                  <select
                    value={newSection.icon}
                    onChange={(e) => setNewSection({ ...newSection, icon: e.target.value })}
                    className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${isDark
                      ? 'bg-gray-700 border-gray-600 text-white'
                      : 'bg-white border-gray-300 text-black'
                      }`}
                  >
                    <option value="Database">Database</option>
                    <option value="Users">Users</option>
                    <option value="FileText">File Text</option>
                    <option value="Settings">Settings</option>
                    <option value="BarChart">Bar Chart</option>
                    <option value="PieChart">Pie Chart</option>
                    <option value="Activity">Activity</option>
                    <option value="Map">Map</option>
                    <option value="Home">Home</option>
                    <option value="Building">Building</option>
                  </select>
                </div>
              )}

              {/* Description (for full sections) */}
              {newSection.type === 'full_section' && (
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Description
                  </label>
                  <textarea
                    value={newSection.description}
                    onChange={(e) => setNewSection({ ...newSection, description: e.target.value })}
                    placeholder="Describe what this section is for"
                    rows={3}
                    className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${isDark
                      ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                      : 'bg-white border-gray-300 text-black placeholder-gray-500'
                      }`}
                  />
                </div>
              )}

              {/* Form Fields (only for form and full_section types) */}
              {(newSection.type === 'form' || newSection.type === 'full_section') && (
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className={`block text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                      Form Fields
                    </label>
                    <button
                      onClick={addField}
                      className={`px-2 py-1 rounded text-sm font-medium transition-colors ${isDark
                        ? 'bg-green-600 hover:bg-green-700 text-white'
                        : 'bg-green-500 hover:bg-green-600 text-white'
                        }`}
                    >
                      <Plus className="w-3 h-3 inline mr-1" />
                      Add Field
                    </button>
                  </div>

                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {/* Field headers */}
                    <div className="flex items-center space-x-2 text-xs font-medium text-gray-500 mb-1">
                      <span className="flex-1">Field Name</span>
                      <span className="w-20 text-center">Type</span>
                      <span className="w-16 text-center">Required</span>
                      <span className="w-16 text-center">Show UI</span>
                      <span className="w-6"></span>
                    </div>
                    {newSection.fields.map((field, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={field.name}
                          onChange={(e) => updateField(index, 'name', e.target.value)}
                          placeholder="Field name"
                          className={`flex-1 px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${isDark
                            ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                            : 'bg-white border-gray-300 text-black placeholder-gray-500'
                            }`}
                        />
                        <select
                          value={field.type}
                          onChange={(e) => updateField(index, 'type', e.target.value)}
                          className={`w-20 px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${isDark
                            ? 'bg-gray-700 border-gray-600 text-white'
                            : 'bg-white border-gray-300 text-black'
                            }`}
                        >
                          <option value="string">Text</option>
                          <option value="int">Number</option>
                          <option value="float">Decimal</option>
                          <option value="bool">Yes/No</option>
                          <option value="date">Date</option>
                        </select>
                        <div className="w-16 flex justify-center">
                          <input
                            type="checkbox"
                            checked={field.required}
                            onChange={(e) => updateField(index, 'required', e.target.checked)}
                            className="w-4 h-4"
                            title="Required field"
                          />
                        </div>
                        <div className="w-16 flex justify-center">
                          <input
                            type="checkbox"
                            checked={field.show_ui}
                            onChange={(e) => updateField(index, 'show_ui', e.target.checked)}
                            className="w-4 h-4"
                            title="Show on UI"
                          />
                        </div>
                        {newSection.fields.length > 1 && (
                          <button
                            onClick={() => removeField(index)}
                            className={`p-1 rounded transition-colors ${isDark ? 'hover:bg-red-700 text-red-400' : 'hover:bg-red-100 text-red-600'
                              }`}
                          >
                            <X className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex space-x-3 pt-4">
                <button
                  onClick={() => setShowAddSection(false)}
                  className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${isDark
                    ? 'bg-gray-600 hover:bg-gray-700 text-white'
                    : 'bg-gray-500 hover:bg-gray-600 text-white'
                    }`}
                >
                  Cancel
                </button>
                <button
                  onClick={createSection}
                  disabled={!newSection.title.trim()}
                  className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${isDark
                    ? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-blue-800'
                    : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-blue-400'
                    }`}
                >
                  <Save className="w-4 h-4 mr-2 inline" />
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
