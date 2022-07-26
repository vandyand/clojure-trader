(ns playing.gpu
  (:require
   [uncomplicate.clojurecuda.core :as cuda]
   [uncomplicate.commons.core :as commons]
   [uncomplicate.clojurecuda.info :as info]))

(cuda/init)

;; (map commons/info (map cuda/device (range (cuda/device-count))))

;; (cuda/device-count)

(def gpu (cuda/device 0))
(def ctx (cuda/context gpu))

;; Set context
(cuda/current-context! ctx)

;;--------------------------------------------------------------------------------------------------------------

(def gpu-kernel
  "extern \"C\"
         __global__ void gpufn (int n, float *a) {
           int i = blockIdx.x * blockDim.x + threadIdx.x;
           if (i < n) {
             a[i] = a[i] + 1.0f;
           }
       };")

(def gpu-fn (-> gpu-kernel cuda/program cuda/compile! cuda/module (cuda/function "gpufn")))

(cuda/launch! gpu-fn (cuda/grid-1d 256) (cuda/parameters 256 gpu-array))

;;--------------------------------------------------------------------------------------------------------------

(defn dotp [xs ys]
  (reduce + (map * xs ys)))

(def foo (vec (range 100000)))

(time (dotp foo foo))

;;--------------------------------------------------------------------------------------------------------------

;; Allocate memory on gpu
(def gpu-array (cuda/mem-alloc 1024))

;; Allocate memory on host
(def main-array (float-array (range 256)))

;; Copy host memory to the gpu
(cuda/memcpy-host! main-array gpu-array)

(def kernel-source
  "extern \"C\"
         __global__ void increment (int n, float *a) {
           int i = blockIdx.x * blockDim.x + threadIdx.x;
           if (i < n) {
             a[i] = a[i] + 1.0f;
        }
       };")

(def hello-program (cuda/compile! (cuda/program kernel-source)))

(def hello-module (cuda/module hello-program))

(def increment (cuda/function hello-module "increment"))

(cuda/launch! increment (cuda/grid-1d 256) (cuda/parameters 256 gpu-array))

(def result (cuda/memcpy-host! gpu-array (float-array 256)))

(println result)

;;--------------------------------------------------------------------------------------------------------------

(def len 32)

(time
 (do
   (def r1 (mapv + (float-array (range len)) (float-array (range len))))
   (take 10 r1)))


(time
 (do
   (def num-bytes (* len 4))

 ;; Allocate memory on gpu
   (def gxs (cuda/mem-alloc num-bytes))
   (def gys (cuda/mem-alloc num-bytes))

;; Allocate memory on host
   (def xs (float-array (range len)))
   (def ys (float-array (range len)))

;; Copy host memory to the gpu
   (cuda/memcpy-host! xs gxs)
   (cuda/memcpy-host! ys gys)

   (def kernel-source
     "extern \"C\"
         __global__ void increment (int width, float *a, float *b) {
      
           int col = blockIdx.x * blockDim.x + threadIdx.x;
           int row = blockIdx.y * blockDim.y + threadIdx.y;
           int i = col + row * width;
           float val = a[i] + b[i];
      
      printf(\"t.x: %d, t.y: %d, t.z: %d, | b.x %d, b.y %d, b.z %d, | bd.x %d, bd.y %d, bd.z %d | gd.x %d, gd.y %d | i %i | val: %d\\n\", 
                  threadIdx.x, threadIdx.y, threadIdx.z,
                  blockIdx.x, blockIdx.y, blockIdx.z,
                  blockDim.x, blockDim.y, blockDim.z,
                  gridDim.x, gridDim.y,
                  i, val);
      a[i] = val;
      
           //printf(\"%i\\n\",i);
           //if (i < n) {
           //  a[i] = val;
           //}
       };")

   (def c (-> kernel-source cuda/program cuda/compile! cuda/module (cuda/function "increment")))



   (cuda/launch! c (cuda/grid-3d 8 4 1 1 1 1) (cuda/parameters 8 gxs gys))

   (def r2 (cuda/memcpy-host! gxs (float-array len)))

   (take len r2)
  ;;  (println r)
  ;;  (clojure.pprint/pprint r)
   ))


;;--------------------------------------------------------------------------------------------------------------

(def gxs (cuda/mem-alloc 4000))
;; (def gys (cuda/mem-alloc 4000))
;; (def gzs (cuda/mem-alloc 4000))

(def xs (float-array (range 1000)))

(cuda/memcpy-host! xs gxs)

;; (def dot-kernel
;;   "extern \"C\"
;;    __global__ void mult (const float *a, const float *b, float *c) {
;;        int i = blockIdx.x * blockDim.x + threadIdx.x;
;;        c[i] = a[i] + b[i] + 0.0f;
;;    }")

(def test-kernel
  "extern \"C\"
   __global__ void testKernel (int val) {
  printf(\"Message from gpu!\");
   }")

(def testKernel (-> test-kernel cuda/program cuda/compile! cuda/module (cuda/function "testKernel")))

(cuda/launch! testKernel (cuda/grid-1d 1000) (cuda/parameters 1000 gxs))


;; (def num-elements 1000)
;; (def threads-per-block 100)
;; (def blocks-per-grid (int (/ (- (+ num-elements threads-per-block) 1) threads-per-block)))

;; (def xs (-> 1000 range float-array))
;; (def ys (-> 1000 range float-array))
;; (def zs (-> 1000 range float-array))

;; (cuda/memcpy-host! xs gxs)
;; (cuda/memcpy-host! ys gys)
;; (cuda/memcpy-host! zs gzs)

(cuda/launch! mult (cuda/grid-1d num-elements threads-per-block) (cuda/parameters 1000 gxs gys gzs))

(cuda/memcpy-host! gzs (float-array (range 1000)))

(println "solution: " zs)

