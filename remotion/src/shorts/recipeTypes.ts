export interface RecipeCharacterLayer {
  presence: string;
  position: string;
  scale: number;
  pose_intent: string;
  body_type: string;
  head: string;
  emotion: string;
  motion: string;
  gesture: string;
}

export interface RecipeComponentLayer {
  role: string;
  component_type: string;
  position: string;
  emphasis_words: string[];
}

export interface RecipeMemeLayer {
  role: string;
  style: string;
  timing: string;
  intensity: number;
}

export interface RecipeCamera {
  motion: string;
  punch_zoom_on?: string | null;
}

export interface RecipeTransition {
  transition_in: string;
  transition_out: string;
}

export interface VisualRecipe {
  recipe_id: string;
  layout: string;
  intent: string;
  attention_strategy: string;
  background_image: string;
  character: RecipeCharacterLayer;
  component: RecipeComponentLayer;
  meme: RecipeMemeLayer;
  camera: RecipeCamera;
  transition: RecipeTransition;
}
