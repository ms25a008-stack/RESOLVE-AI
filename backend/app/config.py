from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    demo_mode: bool = False
    supabase_url: str = ''
    supabase_anon_key: str = ''
    supabase_service_role_key: str = ''
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-2.5-flash'
    gemini_free_tier_confirmed: bool = False
    frontend_origin: str = 'http://localhost:5173'
