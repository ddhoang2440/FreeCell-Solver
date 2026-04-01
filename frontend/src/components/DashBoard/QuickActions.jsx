import React from "react";
import {
  IconArticle,
  IconPackage,
  IconUserPlus,
  IconSettings,
  IconCategory,
} from "@tabler/icons-react";
import { Link } from "react-router-dom";

const QuickActions = () => {
  const actions = [
    {
      icon: <IconArticle className="w-6 h-6" />,
      label: "Tạo Bài Viết",
      color: "bg-blue-500 hover:bg-blue-600",
      description: "Viết bài mới",
      link: "/admin/blogs/create",
    },
    {
      icon: <IconPackage className="w-6 h-6" />,
      label: "Thêm Sản Phẩm",
      color: "bg-green-500 hover:bg-green-600",
      description: "Thêm sản phẩm mới",
      link: "/admin/products/create",
    },
    {
      icon: <IconUserPlus className="w-6 h-6" />,
      label: "Thêm Người Dùng",
      color: "bg-purple-500 hover:bg-purple-600",
      description: "Tạo tài khoản mới",
      link: "/admin/accounts/create",
    },
    {
      icon: <IconCategory className="w-6 h-6" />,
      label: "Quản lý Danh mục",
      color: "bg-orange-500 hover:bg-orange-600",
      description: "Phân loại nội dung",
      link: "/admin/products-category",
    },
    {
      icon: <IconSettings className="w-6 h-6" />,
      label: "Cài Đặt Chung",
      color: "bg-gray-600 hover:bg-gray-700",
      description: "Cấu hình hệ thống",
      link: "/admin/settings/general",
    },
  ];

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Hành động nhanh</h2>
        <p className="text-sm text-gray-500">Thao tác nhanh chóng</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {actions.map((action, index) => (
          <Link
            key={index}
            to={action.link}
            className={`${action.color} text-white p-4 rounded-xl shadow-sm hover:shadow-md transition-all duration-200 transform hover:-translate-y-1 text-left`}
          >
            <div className="flex items-start space-x-3">
              <div className="bg-white/20 p-2 rounded-lg">{action.icon}</div>
              <div>
                <p className="font-semibold">{action.label}</p>
                <p className="text-sm opacity-90 mt-1">{action.description}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default QuickActions;
