import { RouterProvider } from 'react-router';
import router from './routes/Router';
import './css/globals.css';
import UserPreferencesBootstrap from './context/preferences/UserPreferencesBootstrap';

function App() {
  return (
    <>
      <UserPreferencesBootstrap />
      <RouterProvider router={router} />
    </>
  );
}

export default App;
