import React from "react";
import {
  IconChartLine,
  IconChartBar,
  IconChartPie,
  IconCalendar,
} from "@tabler/icons-react";

const Charts = () => {
  const userData = [65, 78, 90, 81, 56, 55, 40, 72, 85, 92, 78, 99];
  const orderData = [45, 60, 75, 51, 49, 62, 70, 91, 88, 76, 82, 95];
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];

  const roleDistribution = [
    { name: "Customer", value: 65, color: "#3b82f6" },
    { name: "Staff", value: 20, color: "#10b981" },
    { name: "Admin", value: 15, color: "#8b5cf6" },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-800 flex items-center">
            <IconChartLine className="w-5 h-5 mr-2 text-blue-500" />
            Phân tích & Xu hướng
          </h2>
          <p className="text-sm text-gray-500">Dữ liệu 12 tháng gần nhất</p>
        </div>
        <div className="flex items-center space-x-2">
          <IconCalendar className="w-5 h-5 text-gray-400" />
          <select className="border border-gray-300 rounded-lg px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option>12 tháng qua</option>
            <option>30 ngày qua</option>
            <option>7 ngày qua</option>
          </select>
        </div>
      </div>
      <div className="mb-8">
        <h3 className="font-medium text-gray-700 mb-4">
          Người dùng đăng ký & Đơn hàng
        </h3>
        <div className="h-64 relative">
          <div className="absolute inset-0 flex flex-col justify-between">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="border-t border-gray-100"></div>
            ))}
          </div>
          <div className="absolute inset-0 flex items-end">
            <div className="flex-1 flex items-end justify-around">
              {userData.map((value, index) => (
                <div key={index} className="relative w-6">
                  <div
                    className="w-4 bg-blue-500/20 rounded-t absolute bottom-0 left-1"
                    style={{ height: `${value}%` }}
                  >
                    <div className="absolute -top-2 left-0 right-0 flex justify-center">
                      <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="absolute inset-0 flex items-end">
            <div className="flex-1 flex items-end justify-around">
              {orderData.map((value, index) => (
                <div key={index} className="relative w-6">
                  <div
                    className="w-4 bg-green-500/20 rounded-t absolute bottom-0 right-1"
                    style={{ height: `${value}%` }}
                  >
                    <div className="absolute -top-2 left-0 right-0 flex justify-center">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="absolute -bottom-8 left-0 right-0 flex justify-around">
            {months.slice(0, 12).map((month, index) => (
              <div
                key={index}
                className="text-xs text-gray-500 w-6 text-center"
              >
                {month}
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center space-x-6 mt-10">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
            <span className="text-sm text-gray-600">Người dùng đăng ký</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
            <span className="text-sm text-gray-600">Đơn hàng</span>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="font-medium text-gray-700 mb-4 flex items-center">
            <IconChartPie className="w-5 h-5 mr-2 text-purple-500" />
            Phân bổ vai trò
          </h3>
          <div className="flex items-center justify-center h-48">
            <div className="relative w-32 h-32">
              {/* Pie chart segments */}
              {/* {roleDistribution.reduce(
                (acc, item, index, arr) => {
                  const prevPercent = acc.prevPercent;
                  const percent = (item.value / 100) * 360;
                  const gradientId = `gradient-${index}`;

                  acc.segments.push(
                    <circle
                      key={index}
                      cx="64"
                      cy="64"
                      r="48"
                      fill="none"
                      stroke={`url(#${gradientId})`}
                      strokeWidth="24"
                      strokeDasharray={`${percent} 360`}
                      strokeDashoffset={`${-prevPercent}`}
                      transform="rotate(-90 64 64)"
                    />
                  );

                  acc.gradients.push(
                    <linearGradient key={gradientId} id={gradientId}>
                      <stop
                        offset="0%"
                        stopColor={item.color}
                        stopOpacity="0.8"
                      />
                      <stop
                        offset="100%"
                        stopColor={item.color}
                        stopOpacity="1"
                      />
                    </linearGradient>
                  );

                  acc.prevPercent += percent;
                  return acc;
                },
                { segments: [], gradients: [], prevPercent: 0 }
              )} */}

              <svg width="128" height="128" viewBox="0 0 128 128">
                <defs>
                  {roleDistribution.map((_, index) => (
                    <linearGradient key={index} id={`gradient-${index}`}>
                      <stop
                        offset="0%"
                        stopColor={roleDistribution[index].color}
                        stopOpacity="0.8"
                      />
                      <stop
                        offset="100%"
                        stopColor={roleDistribution[index].color}
                        stopOpacity="1"
                      />
                    </linearGradient>
                  ))}
                </defs>
                {/* {roleDistribution.map((_, index) => {
                  const prevPercent = roleDistribution
                    .slice(0, index)
                    .reduce((sum, item) => sum + (item.value / 100) * 360, 0);
                  const percent = (roleDistribution[index].value / 100) * 360;

                  return (
                    <circle
                      key={index}
                      cx="64"
                      cy="64"
                      r="48"
                      fill="none"
                      stroke={`url(#gradient-${index})`}
                      strokeWidth="24"
                      strokeDasharray={`${percent} 360`}
                      strokeDashoffset={`${-prevPercent}`}
                      transform="rotate(-90 64 64)"
                    />
                  );
                })} */}
              </svg>
            </div>
          </div>
          <div className="space-y-2 mt-4">
            {roleDistribution.map((role, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center">
                  <div
                    className="w-3 h-3 rounded-full mr-2"
                    style={{ backgroundColor: role.color }}
                  ></div>
                  <span className="text-sm text-gray-600">{role.name}</span>
                </div>
                <span className="text-sm font-medium">{role.value}%</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h3 className="font-medium text-gray-700 mb-4 flex items-center">
            <IconChartBar className="w-5 h-5 mr-2 text-orange-500" />
            Bài viết theo danh mục
          </h3>
          <div className="space-y-3">
            {[
              { category: "Công nghệ", count: 45, color: "bg-blue-500" },
              { category: "Kinh doanh", count: 32, color: "bg-green-500" },
              { category: "Giáo dục", count: 28, color: "bg-purple-500" },
              { category: "Giải trí", count: 22, color: "bg-orange-500" },
              { category: "Sức khỏe", count: 18, color: "bg-red-500" },
            ].map((item, index) => (
              <div key={index} className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{item.category}</span>
                  <span className="text-sm font-medium">{item.count} bài</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`${item.color} h-2 rounded-full`}
                    style={{ width: `${(item.count / 45) * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Charts;
