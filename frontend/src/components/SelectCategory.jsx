// import React from "react";

// const SelectCategory = (items, level = 0) => {
//   return items.map((item) => {
//     const prefix = "-- ".repeat(level);

//     return (
//       <React.Fragment key={item._id}>
//         <option value={item._id}>
//           {prefix}
//           {item.title}
//         </option>

//         {item.children &&
//           item.children.length > 0 &&
//           SelectCategory(item.children, level + 1)}
//       </React.Fragment>
//     );
//   });
// };
// export default SelectCategory;
// SelectCategory.jsx
import React from "react";
const SelectCategory = ({ items, level = 0 }) => {
  if (!items || items.length === 0) return null;

  return items.map((item) => {
    const prefix = "-- ".repeat(level);
    const itemId = String(item._id);
    return (
      <React.Fragment key={item._id}>
        <option value={itemId}>
          {prefix}
          {item.title}
        </option>

        {item.children && item.children.length > 0 && (
          <SelectCategory items={item.children} level={level + 1} />
        )}
      </React.Fragment>
    );
  });
};

export default SelectCategory;
