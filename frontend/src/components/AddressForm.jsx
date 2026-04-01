import React from "react";

const AddressForm = ({ userInfo, onChange }) => {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Họ và tên *
        </label>
        <input
          type="text"
          name="fullName"
          value={userInfo.fullName}
          onChange={onChange}
          required
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
          placeholder="Nhập họ và tên"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Số điện thoại *
        </label>
        <input
          type="tel"
          name="phoneNumber"
          value={userInfo.phoneNumber}
          onChange={onChange}
          required
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
          placeholder="Nhập số điện thoại"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Địa chỉ giao hàng *
        </label>
        <textarea
          name="address"
          value={userInfo.address}
          onChange={onChange}
          required
          rows="3"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
          placeholder="Nhập địa chỉ giao hàng chi tiết"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Ghi chú đơn hàng (tùy chọn)
        </label>
        <textarea
          name="note"
          onChange={onChange}
          rows="2"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
          placeholder="Ghi chú về đơn hàng"
        />
      </div>
    </div>
  );
};

export default AddressForm;
