import React, { useState } from "react";

const PaymentForm = ({ onSubmit, loading }) => {
  const [paymentMethod, setPaymentMethod] = useState("cod");

  const paymentMethods = [
    {
      id: "COD",
      name: "Thanh toán khi nhận hàng (COD)",
      icon: "💰",
      description: "Thanh toán tiền mặt khi nhận được hàng",
    },
    {
      id: "BANKING",
      name: "Chuyển khoản ngân hàng",
      icon: "🏦",
      description: "Chuyển khoản qua ngân hàng",
    },
    {
      id: "MOMO",
      name: "Ví điện tử Momo",
      icon: "📱",
      description: "Thanh toán qua ứng dụng Momo",
    },
  ];

  return (
    <div className="space-y-4">
      {paymentMethods.map((method) => (
        <div
          key={method.id}
          className={`p-4 border rounded-lg cursor-pointer transition-all ${
            paymentMethod === method.id
              ? "border-blue-500 bg-blue-50"
              : "border-gray-200 hover:border-gray-300"
          }`}
          onClick={() => setPaymentMethod(method.id)}
        >
          <div className="flex items-center">
            <div className="mr-3 text-2xl">{method.icon}</div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">{method.name}</h3>
                <input
                  type="radio"
                  name="paymentMethod"
                  value={method.id}
                  checked={paymentMethod === method.id}
                  onChange={() => setPaymentMethod(method.id)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                />
              </div>
              <p className="text-sm text-gray-600 mt-1">{method.description}</p>
            </div>
          </div>
        </div>
      ))}

      {paymentMethod === "banking" && (
        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
          <h4 className="font-medium text-gray-900 mb-2">
            Thông tin chuyển khoản
          </h4>
          <div className="space-y-2 text-sm text-gray-600">
            <p>Ngân hàng: Techcombank</p>
            <p>Số tài khoản: 1903 6666 8888</p>
            <p>Chủ tài khoản: CÔNG TY TNHH THƯƠNG MẠI ABC</p>
            <p>Nội dung: Mã đơn hàng + Số điện thoại</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default PaymentForm;
