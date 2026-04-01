import { IconSearch } from "@tabler/icons-react";
import { useState } from "react";
import { useDispatch } from "react-redux";
import useDebounce from "../hooks/useDebounce";
import { useEffect } from "react";
import axios from "axios";
import { useNavigate, useSearchParams } from "react-router-dom";
const SearchBar = ({ onClose }) => {
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const deounceSearch = useDebounce(keyword, 500);
  useEffect(() => {
    const fetchSuggestions = async () => {
      if (deounceSearch.length < 2) {
        setSuggestions([]);
        setShowSuggestions(false);
        return;
      }
      setIsLoading(true);
      try {
        const { data } = await axios.get(`/admin/products`, {
          params: { keyword: deounceSearch },
        });
        console.log(data);
        if (!data.success) {
          throw new Error("Failed to fetch suggestions");
        }
        setSuggestions(data.productsAdmin || []);
        setShowSuggestions(true);
      } catch (error) {
        console.error("Error fetching search suggestions:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSuggestions();
  }, [deounceSearch, deounceSearch.length]);

  const handleChange = (e) => {
    const { value } = e.target;
    setKeyword(value);
  };
  const [searchParams, setSearchParams] = useSearchParams();
  const handleSubmit = () => {
    const params = updateQuery("keyword", keyword);
    navigate({
      pathname: "/search",
      //   search: `?keyword=${encodeURIComponent(keyword)}`,
      search: params.toString(),
    });
    onClose();
    // updateQuery("keyword", keyword);
  };
  const updateQuery = (key, value) => {
    const params = new URLSearchParams(searchParams);
    if (value === "" || value === null || value === undefined) {
      params.delete(key);
    } else {
      params.set(key, value);
    }
    //   if (key !== "page") {
    //     params.set("page", 1);
    //   }
    return params;
  };
  //   const updateQuery = (key, value) => {
  //     setSearchParams((prev) => {
  //       const params = new URLSearchParams(prev);
  //       if (value === "" || value === null || value === undefined) {
  //         params.delete(key);
  //       } else {
  //         params.set(key, value);
  //       }
  //       //   if (key !== "page") {
  //       //     params.set("page", 1);
  //       //   }
  //       return params;
  //     });
  //   };
  const handleSusggestionClick = (suggestion) => {
    navigate(`/products/detail/${suggestion.slug}`);
    setShowSuggestions(false);
    onClose();
    setKeyword("");
  };
  return (
    <>
      <div
        className="fixed inset-0 w-full h-screen bg-gray-700/30 z-50 flex justify-center items-center"
        onClick={onClose}
      >
        <div
          className="w-[50%] h-[50%] bg-white shadow-lg rounded-xl z-60"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="p-4 ">
            <div className="relative flex gap-2">
              <IconSearch className="absolute left-3 top-5 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                name="keyword"
                placeholder="Search"
                value={keyword}
                onChange={handleChange}
                className="pl-10 pr-10 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                className="px-4 py-2 bg-blue-400 rounded-xl hover:scale-95"
                onClick={handleSubmit}
              >
                Search
              </button>
            </div>
            {showSuggestions && keyword.length >= 2 && (
              <div>
                {isLoading ? (
                  <div className="p-4 text-center text-gray-500">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2">Đang tìm kiếm...</p>
                  </div>
                ) : suggestions.length > 0 ? (
                  <div className=" ">
                    <div className="p-4 border-b border-gray-200 bg-gray-50">
                      <p className="text-lg font-medium text-gray-600">
                        Kết quả tìm kiếm cho "
                        <span className="text-blue-600">{deounceSearch}</span>"
                      </p>
                    </div>

                    {suggestions.map((suggestion) => (
                      <div
                        key={suggestion._id}
                        className="p-4 hover:bg-gray-100 cursor-pointer flex items-center gap-4"
                        onClick={() => handleSusggestionClick(suggestion)}
                      >
                        <div className="w-12 h-12 ">
                          <img
                            src={suggestion.thumbnail}
                            alt={suggestion.title}
                            className="w-full h-full rounded-full object-cover"
                          />
                        </div>
                        <div className="flex flex-col">
                          <p className="text-lg font-medium">
                            {suggestion.title}
                          </p>
                          {suggestion.price && (
                            <p className="text-sm text-blue-600 font-semibold">
                              ${suggestion.price.toLocaleString()}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 text-center text-gray-500">
                    <p>Không tìm thấy sản phẩm nào</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};
export default SearchBar;
