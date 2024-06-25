(ns playing.opencl
  (:require [uncomplicate.clojurecl.core :as cl]
            [uncomplicate.clojurecl.info :as info]
            [uncomplicate.clojurecl.internal.utils :refer [with-check]]
            [uncomplicate.clojurecl.internal.protocols :refer [CLMem]]
            [uncomplicate.clojurecl.toolbox :refer [enq-read-float]]
            [uncomplicate.commons.utils :refer [mask]]
            [org.jocl :as jocl]))

(defn create-command-queue [ctx device]
  (let [queue (jocl/clCreateCommandQueue (cl/context-id ctx) (cl/device-id device) 0 (jocl/clCreateCommandQueue))]
    (with-check queue)))

(defn vector-multiplication-demo [vec1 vec2]
  (try
    (println "Starting vector multiplication demo")
    (let [platforms (cl/platforms)
          _ (println "Available platforms:" platforms)
          platform (first platforms)
          _ (println "Using platform:" platform)
          devices (cl/devices platform :gpu)
          _ (println "Available devices:" devices)
          device (first devices)
          _ (println "Using device:" device)
          ctx (cl/context [device])
          _ (println "Created context:" ctx)
          ;; Create command queue using custom function
          queue (create-command-queue ctx device)
          _ (println "Created command queue:" queue)
          num-elements (count vec1)
          buffer-a (cl/cl-buffer ctx (* num-elements 4) :read-only)
          buffer-b (cl/cl-buffer ctx (* num-elements 4) :read-only)
          buffer-result (cl/cl-buffer ctx (* num-elements 4) :write-only)
          _ (println "Created buffers")
          program (cl/program-with-source ctx ["__kernel void vector_mul(__global const float* a, __global const float* b, __global float* result) {
                                                      int gid = get_global_id(0);
                                                      result[gid] = a[gid] * b[gid];
                                                  }"])
          _ (println "Created program with source")
          _ (cl/build-program! program)
          _ (println "Built program")
          kernel (cl/kernel program "vector_mul")
          _ (println "Created kernel")]

      ;; Write data to buffers
      (cl/enq-write! queue buffer-a (float-array vec1) true)
      (println "Wrote vec1 to buffer-a")
      (cl/enq-write! queue buffer-b (float-array vec2) true)
      (println "Wrote vec2 to buffer-b")

      ;; Set kernel arguments
      (cl/set-arg! kernel 0 buffer-a)
      (cl/set-arg! kernel 1 buffer-b)
      (cl/set-arg! kernel 2 buffer-result)
      (println "Set kernel arguments")

      ;; Enqueue kernel for execution
      (cl/enq-kernel! queue kernel (cl/work-size num-elements))
      (println "Enqueued kernel for execution")

      ;; Read back results
      (let [host-result (float-array num-elements)]
        (cl/enq-read! queue buffer-result host-result true)
        (println "Read results from buffer-result")
        (cl/finish! queue)
        (println "Finished command queue")
        (clojure.core/vec host-result)))
    (catch Exception e
      (println "Error during vector multiplication demo" e)
      nil)))

(println (vector-multiplication-demo [1 2 3] [4 5 6]))