import React from "react";
import {
  IconUser,
  IconShoppingCart,
  IconArticle,
  IconLogin,
  IconAlertCircle,
  IconCheck,
  IconClock,
} from "@tabler/icons-react";

const RecentActivity = () => {
  const activities = [
    {
      icon: <IconUser className="w-5 h-5" />,
      user: 'Người dùng "john_doe"',
      action: "vừa đăng ký",
      time: "10:25",
      color: "bg-blue-100 text-blue-600",
      status: "new",
    },
    {
      icon: <IconShoppingCart className="w-5 h-5" />,
      user: "Đơn hàng #ORD-789",
      action: "được tạo bởi alice_smith",
      time: "10:18",
      color: "bg-green-100 text-green-600",
      status: "pending",
    },
    {
      icon: <IconArticle className="w-5 h-5" />,
      user: 'Bài viết "Hướng dẫn mới"',
      action: "đang chờ duyệt",
      time: "09:55",
      color: "bg-yellow-100 text-yellow-600",
      status: "pending",
    },
    {
      icon: <IconLogin className="w-5 h-5" />,
      user: 'Admin "you"',
      action: "đã đăng nhập từ IP 192.168.1.1",
      time: "09:30",
      color: "bg-purple-100 text-purple-600",
      status: "success",
    },
    {
      icon: <IconAlertCircle className="w-5 h-5" />,
      user: 'Bài viết "Khuyến mãi"',
      action: "bị report bởi user123",
      time: "09:15",
      color: "bg-red-100 text-red-600",
      status: "warning",
    },
    {
      icon: <IconCheck className="w-5 h-5" />,
      user: "Đơn hàng #ORD-788",
      action: "đã được xác nhận",
      time: "08:45",
      color: "bg-green-100 text-green-600",
      status: "success",
    },
    {
      icon: <IconClock className="w-5 h-5" />,
      user: "Hệ thống backup",
      action: "hoàn thành lúc 03:00",
      time: "03:00",
      color: "bg-gray-100 text-gray-600",
      status: "info",
    },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 h-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            Hoạt động gần đây
          </h2>
          <p className="text-sm text-gray-500">Cập nhật theo thời gian thực</p>
        </div>
        <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
          Xem tất cả
        </button>
      </div>

      <div className="space-y-4 max-h-160 overflow-y-auto pr-2">
        {activities.map((activity, index) => (
          <div
            key={index}
            className="flex items-start space-x-3 p-3 hover:bg-gray-50 rounded-lg transition-colors"
          >
            <div className={`${activity.color} p-2 rounded-lg`}>
              {activity.icon}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <p className="font-medium text-gray-800 truncate">
                  {activity.user}
                </p>
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  {activity.time}
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-1">{activity.action}</p>

              <div className="flex items-center space-x-2 mt-2">
                <span
                  className={`text-xs px-2 py-1 rounded-full ${
                    activity.status === "new"
                      ? "bg-blue-100 text-blue-600"
                      : activity.status === "pending"
                      ? "bg-yellow-100 text-yellow-600"
                      : activity.status === "success"
                      ? "bg-green-100 text-green-600"
                      : activity.status === "warning"
                      ? "bg-orange-100 text-orange-600"
                      : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {activity.status === "new"
                    ? "Mới"
                    : activity.status === "pending"
                    ? "Chờ xử lý"
                    : activity.status === "success"
                    ? "Thành công"
                    : activity.status === "warning"
                    ? "Cảnh báo"
                    : "Thông tin"}
                </span>

                {activity.status === "pending" && (
                  <button className="text-xs text-blue-600 hover:text-blue-800 font-medium">
                    Xử lý ngay
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Live indicator */}
      <div className="mt-6 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-center space-x-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-sm text-gray-600">
            Đang cập nhật theo thời gian thực
          </span>
        </div>
      </div>
    </div>
  );
};

export default RecentActivity;
