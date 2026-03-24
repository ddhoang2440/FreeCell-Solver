import React from "react";
import {
  IconUsers,
  IconShoppingCart,
  IconCurrencyDollar,
  IconArticle,
  IconLock,
  IconTrendingUp,
  IconTrendingDown,
} from "@tabler/icons-react";

const KpiCards = () => {
  const kpis = [
    {
      title: "Tổng người dùng",
      value: "1,245",
      icon: <IconUsers className="w-6 h-6" />,
      change: "+12%",
      trend: "up",
      color: "bg-blue-500",
      link: "/admin/users",
    },
    {
      title: "Doanh thu hôm nay",
      value: "$3,450",
      icon: <IconCurrencyDollar className="w-6 h-6" />,
      change: "+24%",
      trend: "up",
      color: "bg-green-500",
      link: "/admin/orders",
    },
    {
      title: "Đơn hàng mới",
      value: "42",
      icon: <IconShoppingCart className="w-6 h-6" />,
      change: "+8%",
      trend: "up",
      color: "bg-orange-500",
      link: "/admin/orders?status=pending",
    },
    {
      title: "Bài viết chờ duyệt",
      value: "7",
      icon: <IconArticle className="w-6 h-6" />,
      change: "-2",
      trend: "down",
      color: "bg-yellow-500",
      link: "/admin/blogs?status=pending",
    },
    {
      title: "Tài khoản bị khóa",
      value: "3",
      icon: <IconLock className="w-6 h-6" />,
      change: "0",
      trend: "neutral",
      color: "bg-red-500",
      link: "/admin/users?status=blocked",
    },
  ];

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">
          Tổng quan hệ thống
        </h2>
        <p className="text-sm text-gray-500">Cập nhật thời gian thực</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {kpis.map((kpi, index) => (
          <div
            key={index}
            className="bg-white rounded-xl shadow-sm border p-5 hover:shadow-md transition-shadow cursor-pointer"
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`${kpi.color} p-2 rounded-lg`}>
                <div className="text-white">{kpi.icon}</div>
              </div>
              <div
                className={`flex items-center space-x-1 text-sm ${
                  kpi.trend === "up"
                    ? "text-green-600"
                    : kpi.trend === "down"
                    ? "text-red-600"
                    : "text-gray-500"
                }`}
              >
                {kpi.trend === "up" ? (
                  <IconTrendingUp className="w-4 h-4" />
                ) : kpi.trend === "down" ? (
                  <IconTrendingDown className="w-4 h-4" />
                ) : null}
                <span>{kpi.change}</span>
              </div>
            </div>

            <h3 className="text-2xl font-bold text-gray-800 mb-1">
              {kpi.value}
            </h3>
            <p className="text-gray-600 text-sm mb-3">{kpi.title}</p>

            <a
              href={kpi.link}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center"
            >
              Xem chi tiết
              <svg
                className="w-4 h-4 ml-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </a>
          </div>
        ))}
      </div>
    </div>
  );
};

export default KpiCards;
