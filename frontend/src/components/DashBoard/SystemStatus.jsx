import React from "react";
import {
  IconServer,
  IconDatabase,
  IconCloud,
  IconFileUpload,
  IconSettings,
  IconCheck,
  IconAlertTriangle,
  IconX,
} from "@tabler/icons-react";

const SystemStatus = () => {
  const systemComponents = [
    {
      name: "API / Backend",
      status: "online",
      icon: <IconServer className="w-5 h-5" />,
      details: "Phản hồi < 200ms",
      uptime: "99.9%",
    },
    {
      name: "Cơ sở dữ liệu",
      status: "online",
      icon: <IconDatabase className="w-5 h-5" />,
      details: "45 connections",
      uptime: "100%",
    },
    {
      name: "Bộ nhớ đệm (Redis)",
      status: "warning",
      icon: <IconCloud className="w-5 h-5" />,
      details: "Hit rate: 92%",
      uptime: "98.5%",
    },
    {
      name: "Tệp tin Upload",
      status: "error",
      icon: <IconFileUpload className="w-5 h-5" />,
      details: "Dung lượng > 85%",
      uptime: "95.2%",
    },
    {
      name: "Cấu hình chung",
      status: "online",
      icon: <IconSettings className="w-5 h-5" />,
      details: "Logo, Site Name, Favicon",
      uptime: "100%",
    },
  ];

  const getStatusIcon = (status) => {
    switch (status) {
      case "online":
        return <IconCheck className="w-4 h-4 text-green-500" />;
      case "warning":
        return <IconAlertTriangle className="w-4 h-4 text-yellow-500" />;
      case "error":
        return <IconX className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "online":
        return "bg-green-100 text-green-800 border-green-200";
      case "warning":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "error":
        return "bg-red-100 text-red-800 border-red-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            Trạng thái hệ thống
          </h2>
          <p className="text-sm text-gray-500">Giám sát sức khỏe kỹ thuật</p>
        </div>
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
            <span>Online</span>
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-yellow-500 rounded-full mr-1"></div>
            <span>Warning</span>
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-red-500 rounded-full mr-1"></div>
            <span>Error</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {systemComponents.map((component, index) => (
          <div
            key={index}
            className={`border rounded-lg p-4 ${getStatusColor(
              component.status
            )}`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                {component.icon}
                <span className="font-medium">{component.name}</span>
              </div>
              {getStatusIcon(component.status)}
            </div>

            <p className="text-sm opacity-90 mb-2">{component.details}</p>

            <div className="flex items-center justify-between mt-4 pt-3 border-t">
              <span className="text-xs">Uptime:</span>
              <span className="text-xs font-medium">{component.uptime}</span>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-white/50 rounded-full h-1.5 mt-2">
              <div
                className={`h-1.5 rounded-full ${
                  component.status === "online"
                    ? "bg-green-500"
                    : component.status === "warning"
                    ? "bg-yellow-500"
                    : "bg-red-500"
                }`}
                style={{
                  width:
                    component.status === "error"
                      ? "85%"
                      : component.status === "warning"
                      ? "92%"
                      : "100%",
                }}
              ></div>
            </div>
          </div>
        ))}
      </div>

      {/* System metrics */}
      <div className="mt-6 pt-6 border-t border-gray-100">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">CPU Usage</span>
              <span className="text-sm font-medium text-green-600">42%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div
                className="bg-green-500 h-2 rounded-full"
                style={{ width: "42%" }}
              ></div>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Memory</span>
              <span className="text-sm font-medium text-blue-600">68%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div
                className="bg-blue-500 h-2 rounded-full"
                style={{ width: "68%" }}
              ></div>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Disk Space</span>
              <span className="text-sm font-medium text-orange-600">85%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div
                className="bg-orange-500 h-2 rounded-full"
                style={{ width: "85%" }}
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemStatus;
