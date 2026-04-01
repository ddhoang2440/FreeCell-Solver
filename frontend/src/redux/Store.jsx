import { configureStore } from "@reduxjs/toolkit";
import authreducer from "./AuthRedux";

export const store = configureStore({
  reducer: {
    auth: authreducer,
  },
});
