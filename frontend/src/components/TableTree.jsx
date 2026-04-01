import { useNavigate } from "react-router-dom";
import React from "react";
import { useState } from "react";
import { useDispatch } from "react-redux";
import {
  deleteProductCategory,
  fetchProductCategory,
  fetchProductCategoryDelete,
  updateProduct,
} from "../redux/admin/ProductCategoryAdminRedux";
import { useSelector } from "react-redux";

const TableTree = ({ productsCategory, level = 0, isDelete }) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { currentRole } = useSelector((state) => state.roles);
  const permission = currentRole?.permissions;
  const [selectedProducts, setSelectedProducts] = useState([]);
  const toggleStatus = async (_id, currentStatus) => {
    const newStatus = currentStatus === "active" ? "inactive" : "active";
    try {
      await dispatch(
        updateProduct({
          _id,
          productData: { status: newStatus },
        })
      ).unwrap();
      await Promise.all([
        dispatch(fetchProductCategory()).unwrap(),
        dispatch(fetchProductCategoryDelete()).unwrap(),
      ]);
      console.log("Status updated successfully");
    } catch (error) {
      console.error("Failed to update status:", error);
    }
  };
  const handleDelete = async (_id) => {
    console.log("Delete product with ID:", _id);
    try {
      const yes = window.confirm(
        "Are you sure you want to delete this product?"
      );
      if (!yes) return;
      await dispatch(deleteProductCategory([_id])).unwrap();
      dispatch(fetchProductCategory());
      dispatch(fetchProductCategoryDelete());
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };
  const handleRestore = async (_id) => {
    try {
      const yes = window.confirm(
        "Are you sure you want to restore this product?"
      );
      if (!yes) return;
      await dispatch(
        updateProduct({ _id, productData: { deleted: false } })
      ).unwrap();
      await Promise.all([
        dispatch(fetchProductCategory()).unwrap(),
        dispatch(fetchProductCategoryDelete()).unwrap(),
      ]);
    } catch (error) {
      console.error("Restore failed:", error);
    }
  };
  return (
    <>
      {productsCategory.map((item, idx) => {
        const prefix = "-- ".repeat(level);
        const isSelected = (id) =>
          selectedProducts.some((prod) => prod.id === id);
        const getPosition = (id) =>
          selectedProducts.find((prod) => prod.id === id).position;
        const handleCheckboxClick = (product, checked) => {
          setSelectedProducts((prevSelected) => {
            if (checked) {
              return [
                ...prevSelected,
                { id: product._id, position: product.position },
              ];
            } else {
              return prevSelected.filter((prod) => prod.id !== product._id);
            }
          });
        };
        const handlePositionChange = (productId, newPosition) => {
          const Position = parseInt(newPosition) || 0;
          setSelectedProducts((prevSelected) =>
            prevSelected.map((prod) =>
              prod.id === productId ? { ...prod, position: Position } : prod
            )
          );
        };
        return (
          <React.Fragment key={idx}>
            <tr key={item._id}>
              <td className="border border-gray-300 p-2">
                <input
                  type="checkbox"
                  className="size-5"
                  value={item._id}
                  checked={isSelected(item._id)}
                  onChange={(e) => handleCheckboxClick(item, e.target.checked)}
                />
              </td>
              <td className="border border-gray-300 p-2">{item.index}</td>
              <td className="border border-gray-300 p-2">
                <img
                  src={item.thumbnail}
                  alt="Ảnh"
                  className="w-16 h-16 object-cover rounded-full mx-auto"
                />
              </td>
              <td className="border border-gray-300 px-2 text-left text-xl font-semibold">
                {prefix}
                {item.title}
              </td>
              <td className="border border-gray-300 p-2">
                <input
                  type="number"
                  name="position"
                  value={
                    isSelected(item._id) ? getPosition(item._id) : item.position
                  }
                  className="w-[50%] border px-2 py-1 rounded-lg text-center"
                  onChange={(e) =>
                    handlePositionChange(item._id, e.target.value)
                  }
                />
              </td>
              <td className="border border-gray-300 p-2">
                <button
                  className={`px-3 py-2 rounded-2xl cursor-pointer ${
                    item.status === "active" ? "bg-green-400" : "bg-red-400"
                  }`}
                  onClick={() => toggleStatus(item._id, item.status)}
                >
                  {item.status}
                </button>
              </td>

              <td className="border border-gray-300 p-2">
                {isDelete ? (
                  <div>
                    <button
                      className="px-4 py-2 bg-orange-500 rounded-2xl text-white mr-2 cursor-pointer active:scale-95"
                      onClick={() => handleRestore(item._id)}
                    >
                      Khôi phục
                    </button>
                  </div>
                ) : (
                  <div>
                    <button
                      className="px-4 py-2 bg-green-500 rounded-2xl text-white mr-2 cursor-pointer"
                      onClick={() =>
                        navigate(`/admin/products-category/detail/${item._id}`)
                      }
                    >
                      Chi tiết
                    </button>
                    {permission.includes("product-category_edit") && (
                      <button
                        className="px-4 py-2 bg-blue-500 rounded-2xl text-white cursor-pointer"
                        onClick={() =>
                          navigate(`/admin/products-category/edit/${item._id}`)
                        }
                      >
                        Sửa
                      </button>
                    )}
                    {permission.includes("product-category_delete") && (
                      <button
                        className="px-4 py-2 bg-red-500 rounded-2xl text-white cursor-pointer"
                        onClick={() => handleDelete(item._id)}
                      >
                        Xóa
                      </button>
                    )}
                  </div>
                )}
              </td>
            </tr>
            {item.children && item.children.length > 0 && (
              <TableTree
                key={`child_${item._id}`}
                productsCategory={item.children}
                level={level + 1}
                isDelete={isDelete}
              />
            )}
          </React.Fragment>
        );
      })}
    </>
  );
};

export default TableTree;
