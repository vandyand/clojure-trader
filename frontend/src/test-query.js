import React from "react";
import { useQuery } from "@tanstack/react-query";

// Simple example of React Query v4 usage
export function ExampleComponent() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["example"],
    queryFn: () =>
      fetch("https://api.example.com/data").then((res) => res.json()),
    refetchInterval: 5000,
  });

  // This is the correct pattern for React Query v4
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!data) return <div>No data available</div>;

  return <div>{JSON.stringify(data)}</div>;
}
