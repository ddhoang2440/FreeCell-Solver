import { Link } from "react-router-dom";

const CartSummary = ({ cartProducts }) => {
  return (
    <div>
      <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
        {cartProducts.map((item, index) => {
          return (
            <div key={index} className="flex items-center py-3 border-b">
              <div className="shrink-0 w-16 h-16 bg-gray-100 rounded-lg overflow-hidden">
                <img
                  src={item.product_id?.thumbnail}
                  alt={item.product_id?.title}
                  className="w-full h-full object-cover"
                />
              </div>

              <div className="ml-4 flex-1">
                <Link
                  to={`/products/detail/${item.product_id?.slug}`}
                  className="font-medium text-gray-900 hover:text-blue-600 line-clamp-1"
                >
                  {item.product_id?.title}
                </Link>

                <div className="flex items-center justify-between mt-1">
                  <div className="flex items-center space-x-4">
                    <span className="text-sm text-gray-500">
                      Số lượng: {item.quantity}
                    </span>
                  </div>

                  <div className="text-right">
                    {item.product_id?.discountPercentage > 0 ? (
                      <>
                        <div className="text-gray-400 line-through">
                          {(
                            item.product_id?.price * item.quantity
                          ).toLocaleString("vi-VN")}
                          đ
                        </div>
                        <div className="text-red-600 font-medium text-lg">
                          {(
                            item.product_id?.price *
                            item.quantity *
                            (1 - item.product_id?.discountPercentage / 100)
                          ).toLocaleString("vi-VN")}
                          đ
                        </div>
                      </>
                    ) : (
                      <div className="text-gray-900 font-medium text-lg">
                        {(
                          item.product_id?.price * item.quantity
                        ).toLocaleString("vi-VN")}
                        đ
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CartSummary;
