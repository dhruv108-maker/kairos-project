import { RouterProvider } from 'react-router';
import router from './routes/Router';
import './css/globals.css';
import { Toaster } from './components/ui/sonner';

function App() {
  return (
    <>
    
      <RouterProvider router={router} />
      <Toaster richColors position="top-right" />
    </>
  );
}

export default App;
