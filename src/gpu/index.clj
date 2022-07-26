(ns gpu.index
  (:require
   [uncomplicate.clojurecuda.core :as cuda]
   [uncomplicate.commons.core :as commons]
   [uncomplicate.clojurecuda.info :as info]
   [gpu.util :as gutil]))

(gutil/gpu-init)
(cuda/init)
(-> 0 cuda/device cuda/context cuda/current-context!)

(defn gpu-fn [kernel-fn kernel-fn-name & kernel-args]
  (let [num-elements (count (first kernel-args))
        bytesize (gutil/type->bytesize (ffirst kernel-args))
        num-bytes (* num-elements bytesize)
        gxs (cuda/mem-alloc num-bytes)
        gys (cuda/mem-alloc num-bytes)]
    (cuda/memcpy-host! (first kernel-args) gxs)
    (cuda/memcpy-host! (second kernel-args) gys)
    (let [gpu-fn (-> kernel-fn cuda/program cuda/compile! cuda/module (cuda/function kernel-fn-name))]
      (cuda/launch! gpu-fn (cuda/grid-1d num-elements) (cuda/parameters num-elements gxs gys))
      (cuda/memcpy-host! gxs (double-array num-elements)))))


(defn add [xs ys]
  (let [kernel "extern \"C\"
         __global__ void add (int width, double *a, double *b) {
           int col = blockIdx.x * blockDim.x + threadIdx.x;
           int row = blockIdx.y * blockDim.y + threadIdx.y;
           int i = col + row * width;
           a[i] = a[i] + b[i];
       };"
        kernel-fn-name "add"]
    (gpu-fn kernel kernel-fn-name xs ys)))



(defn mult [xs ys]
  (let [kernel "extern \"C\"
         __global__ void mult (int width, double *a, double *b) {
      
           int col = blockIdx.x * blockDim.x + threadIdx.x;
           int row = blockIdx.y * blockDim.y + threadIdx.y;
           int i = col + row * width;
           a[i] = a[i] * b[i];
       };"
        kernel-fn-name "mult"]
    (gpu-fn kernel kernel-fn-name xs ys)))

(comment
  (let [len 100000000
        xs (double-array (range len))
        ys (double-array (map inc (range len)))]
    (time (mult xs ys)))
  (let [len 10000000
        xs (double-array (range len))
        ys (double-array (map inc (range len)))]
    (time (add xs ys))))

(comment
  (do
    (def len 10000000)
    (def xs (double-array (range len)))

    (time (mult xs xs))
    (time (mapv * xs xs))))