from PIL import Image, ImageDraw, ImageFont

TERMINAL_LOGS = False

# Colour values
RGBA_TRANSPARENT = (0, 0, 0, 0)
RGBA_BACKGROUND  = (255, 255, 255, 255)
RGBA_TEXT        = (0, 0, 0, 255)

def calculate_box_to_crop_out_whitespace_from_img(img, debug = False) :
	
	if debug :
		print(f"----------\n")

	# Removes most unnecessary pixels (whitespace) from image
	# Finds the x coordinate of the leftmost and rightmost pixel
	# Finds the y coordinate of the topmost and bottommost pixel

	# Loads pixel map
	img_w, img_h  = img.size
	img_pixel_map = img.load()

	left   = img_w # Moves right
	top    = img_h # Moves down
	right  = 0     # Moves left
	bottom = 0     # Moves up

	# Keeping some whitespace for safety
	margin = 1

	# Iterates through every pixel
	for x in range(img_w) :
		for y in range(img_h) :
			
			# Not whitespace
			if (img_pixel_map[x, y] not in [RGBA_TRANSPARENT, RGBA_BACKGROUND]) and (x not in [0, img_w - 1]) and (y not in [0, img_h - 1]) :

				# ±1 because current pixel is not a whitespace
				# Hence cropping at x instead of (x ± 1) will remove part of the character

				if x < left :
					left = x - 1

				if x > right :
					right = x + 1

				if y < top :
					top = y - 1

				if y > bottom :
					bottom = y + 1

	# Adding margin for safety
	if left != 0 :
		left = left - margin

	if top != 0 :
		top = top - margin

	if right != (img_w - 1) :
		right = right + margin

	if bottom != (img_h - 1) :
		bottom = bottom + margin

	if debug :
		print(f"Box          = {(left, top, right, bottom)}\nMargin added = {margin}\n")

	return (left, top, right, bottom)

def calculate_wh_of_rendered_text(text, font, anchor = None, debug = False) :

	if debug :
		print(f"----------\n")

	# Anchor is dependent on font being used

	# This image is a buffer
	render_text_on = Image.new("RGBA", (0, 0), RGBA_TRANSPARENT)
	draw_layer     = ImageDraw.Draw(render_text_on)

	# Gets text bounding box
	# ... = (left, top, right, bottom)
	text_bbox = draw_layer.textbbox(xy = (0, 0), text = text, font = font, anchor = anchor)

	# Calculates width and height
	text_w = text_bbox[2] - text_bbox[0]
	text_h = text_bbox[3] - text_bbox[1]

	# Font tries to draw character taking an equal amount of space (pixels) above and below baseline
	# i.e. Half of the character is above the baseline and half of the character is below the baseline

	# The offset shifts the character from (0, 0) to (left, top)
	# The character then satisfies the half above and half below baseline condition

	# Assuming that the text anchor is "mm"

	left = text_bbox[0] 
	top  = text_bbox[1]

	# Releases memory
	render_text_on.close()

	if debug :
		print(f"Text          = {text}\nBounding box  = {text_bbox}\nWidth, Height = {text_w, text_h}\nLeft, Top     = {left, top}\n")

	return (text_w, text_h, left, top)

def create_img_of_text(text, font, anchor = None, debug = False) :
	
	if debug :
		print(f"----------\n")

	# Calculates width and height of character when drawn
	text_w, text_h, left, top = calculate_wh_of_rendered_text(text = text, font = font, anchor = anchor, debug = debug)

	text_img = Image.new("RGBA", (text_w, text_h), RGBA_TRANSPARENT)
	draw_img = ImageDraw.Draw(text_img)

	# Draws character with an offset

	# Shift character from (left, top) to (0, 0)
	# Since the width and height of the image = the width and height of the character,
	# An image of only the character is created with minimal whitespace

	# This shift works well for alphabets but not so much for vowels
	# Because vowels have a lot of whitespace in the character/unicode itself

	draw_img.text(
		xy   = (- left, - top),
		text = text,
		font = font,
		fill = RGBA_TEXT
		)

	if debug :
		print(f"Creating image of text\nText          = {text}\nWidth, Height = {text_w, text_h}\nx, y          = {- left, - top}\n")

	# Returns a dict for ease of use (QoL)

	return {
		"img"           : text_img,
		"text_bbox"     : (text_w, text_h, left, top),
		"left_top_used" : (- left, - top)
		}

class ArabicWord :

	# Arabic characters usually have UTF-8 encoding
	ENCODING = "utf-8"

	def __init__(self, word_string, font_path = None, font_size = 12) :
		
		self.word_string = word_string

		# Init PIL font
		self.font      = ImageFont.truetype(font_path, font_size)
		self.font_size = font_size

	def tokenize_word(self, debug = False) :

		if debug :
			print(f"----------\n")

		# Seperates alphabets and vowels in word
		# Alphabets can have more than one vowel associated to them (2 max)

		alphabets = []
		vowels    = []

		# Stores vowels corresponding to the current alphabet
		# i.e. vowels for alphabets[-1] throughout iteration
		vowels_for_this_alphabet = []

		for i in self.word_string :

			# Vowel
			# Arabic vowels unicode values usually start with b'\xd9\...'
			if str(i.encode(ArabicWord.ENCODING))[3 : 6] in ["xd9"] :
				vowels_for_this_alphabet.append(i)

			# Alphabet
			else :
				alphabets.append(i)
				vowels.append(vowels_for_this_alphabet)

				# Resets for next alphabet
				vowels_for_this_alphabet = []

		if debug :

			# Removes [] from vowels
			print(f"Word has {len(alphabets)} alphabets and {len([i for i in vowels if i])} vowels\n")

		return alphabets, vowels

	def calculate_xy_and_wh_of_each_alphabet(self, alphabets, offset_x = 0, offset_y = 0, debug = False) :
		
		if debug :
			print(f"----------\n")

		# Identifies each unique alphabet
		alphabets_unique = []
		
		for i in alphabets :

			# Unique alphabet
			if i not in alphabets_unique :
				alphabets_unique.append(i)

		if debug :
			print(f"Word has {len(alphabets_unique)} different unique alphabets\n")

		# Calculates the width and height of each alphabet when drawn
		alphabets_unique_wh = {}

		for i in alphabets_unique :
			alphabets_unique_wh[i] = calculate_wh_of_rendered_text(text = i, font = self.font, debug = debug)

		# Calculates where each alphabet will be drawn
		# i.e. (left, top)

		# When alphabet is drawn at (0, 0), for example
		# The actual alphabet (no whitespace) is drawn at (0 + left, 0 + top)
		# But the actual coordinate passed as parameters for xy is (0, 0) instead of (0 + left, 0 + top)
		
		alphabets_xy = []

		for i, a in enumerate(alphabets) :
			
			# Calculates the sum of the widths of each alphabet before this one
			a_x = offset_x + sum([alphabets_unique_wh[j][0] for j in alphabets[:i]])

			# Y will usually be constant for all alphabets
			# Y will later be changed depending on what vowels are pasted on top of alphabets and the height that they occupy
			a_y = offset_y

			alphabets_xy.append((a_x, a_y))

			if debug :
				print(f"Alphabet      = {a}\nWidth, Height = {alphabets_unique_wh[a][0], alphabets_unique_wh[a][1]}\nx, y          = {a_x, a_y}\n")

		# Note that these values won't be used to draw alphabets
		# Because there may be cases where alphabets won't be properly joined together (if these values are used)
		# But these values will be used to calculate values for vowels and such

		return alphabets_unique_wh, alphabets_xy

	def create_img_of_each_different_vowels(self, vowels, debug = False) :
		
		if debug :
			print(f"----------\n")

		# Identifies each unique vowels
		vowels_unique = []

		for i in vowels :

			# Variable i is a list of vowels
			for j in i :

				# Unique vowel
				if j not in vowels_unique :
					vowels_unique.append(j)
		
		if debug :
			print(f"Word has {len(vowels_unique)} different unique vowels\n")

		# Processes each unique vowel
		vowels_unique_wh  = {}
		vowels_unique_img = {}

		for i in vowels_unique :

			# Creates images for each unique vowel
			# Calculates the width and height of each vowel when drawn
			vowel_img, vowels_unique_wh[i], _ = create_img_of_text(text = i, font = self.font, debug = debug).values() # Unpacks values from returned dict

			# Images of vowels are cropped to remove whitespace
			# Because some fonts draw vowels with whitespace and others without
			# The images are thus cropped as a standard

			# Crops image of vowel
			vowels_unique_img[i] = vowel_img.crop(box = calculate_box_to_crop_out_whitespace_from_img(img = vowel_img, debug = debug))

		return vowels_unique_wh, vowels_unique_img

	def calculate_xy_of_each_vowel_dependent_of_alphabet(self, vowels, vowels_unique_img, alphabets, alphabets_xy, alphabets_unique_wh, alphabet_vowel_gap_y, debug = False) :

		if debug :
			print(f"----------\n")

		# Classifies vowels
		# Hard-coded because I don't think that there's a way to know where the vowel will be pasted

		# Plus, this maybe can be hard-coded
		# Since vowels stay rather constant in the language

		vowels_up   = ['َ', 'ْ', 'ُ', 'ٌ', 'ً', 'ّ']
		vowels_down = ['ِ', 'ٍ']

		# Calculates where each vowel will be drawn
		# i.e. (left, top)

		vowels_xy = []

		# Also adds a small gap in between vowels and alphabets (= alphabet_vowel_gap_y)

		for i, vowels_for_this_alphabet in enumerate(vowels) :
			this_alphabet = alphabets[i]

			# Naming things is hard, alright!?
			xy_for_these_vowels_for_this_alphabet = []

			# xy where the alphabet is actually drawn = (left, top)
			this_alphabet_actual_wh_xy = alphabets_unique_wh[this_alphabet]

			this_alphabet_actual_left = alphabets_xy[i][0] + this_alphabet_actual_wh_xy[2]
			this_alphabet_actual_top  = alphabets_xy[i][1] + this_alphabet_actual_wh_xy[3]

			for j, v in enumerate(vowels_for_this_alphabet) :
				
				# Centers vowel above/below alphabet on x-axis
				# = A_Left + ((A_Width - V_Width) // 2)

				v_x = this_alphabet_actual_left + ((this_alphabet_actual_wh_xy[0] - vowels_unique_img[v].size[0]) // 2)

				# Calculates y coordinate (top)

				# If an alphabet has more than one vowels,
				# Vowels are next to each other when drawn
				# i.e. Both vowels are drawn above the alphabet

				if (v in vowels_up) or (len(vowels_for_this_alphabet) > 1) :
					
					# An alphabet may have one or two vowels drawn above it

					# Places vowel above alphabet (- to shift vowel's y up)
					# = A_Top - V_Height

					v_y = this_alphabet_actual_top - (vowels_unique_img[v].size[1] + alphabet_vowel_gap_y)

					# There is another vowel for this alphabet
					if (len(vowels_for_this_alphabet) > 1) and (j == 1) :
						last_v = vowels_for_this_alphabet[j - 1]

						# Shifts vowel above next vowel
						v_y = v_y - (vowels_unique_img[last_v].size[1] + alphabet_vowel_gap_y)

				elif v in vowels_down :
					
					# There will normally be only one vowel down

					# Places vowel below alphabet (+ to shift vowel's y down)
					# = A_Top + A_Height

					v_y = this_alphabet_actual_top + this_alphabet_actual_wh_xy[1] + alphabet_vowel_gap_y

				if debug :
					print(f"Vowel         = {v} (for alphabet = {this_alphabet})\nWidth, Height = {vowels_unique_img[v].size}\nx, y          = {v_x, v_y}\n")

				xy_for_these_vowels_for_this_alphabet.append((v_x, v_y))

			vowels_xy.append(xy_for_these_vowels_for_this_alphabet)

		# Note that the images of vowels will be pasted above/below alphabets instead of drawing them with the font
		# So the (left, top) situation that comes when drawing the alphabets with the fonts won't be applicable here

		return vowels_xy

	def create_img_of_word(self, offset_in_alphabets_xy = (0, 0), offset_in_vowels_xy = (0, 0), debug = False) :

		if debug :
			print(f"----------\n")

		# Creates the image of the arabic word by calling methods

		# Seperates alphabets and vowels (tokenizes word)
		alphabets, vowels = self.tokenize_word(debug = debug)

		# Creates images for each different vowels
		_, vowels_unique_img = self.create_img_of_each_different_vowels(vowels = vowels, debug = debug)

		# Calculates width and height of each alphabet
		# Calculates where each alphabet will be drawn

		# These values won't be used to draw alphabets
		# But to calculate where to paste images of vowels

		alphabets_unique_wh, alphabets_xy = self.calculate_xy_and_wh_of_each_alphabet(alphabets = alphabets, debug = debug)

		# Adds a small gap in between vowels and alphabets
		alphabet_vowel_gap_y = int(0.1 * self.font_size)

		# Calculates where to paste images of vowels (i.e. (left, top))
		vowels_xy = self.calculate_xy_of_each_vowel_dependent_of_alphabet(
			vowels               = vowels,
			vowels_unique_img    = vowels_unique_img,
			alphabets            = alphabets,
			alphabets_xy         = alphabets_xy,
			alphabets_unique_wh  = alphabets_unique_wh,
			alphabet_vowel_gap_y = alphabet_vowel_gap_y,
			debug                = debug
			)


		# Some values in vowels_xy are less than 0
		# Then every xy (alphabets and vowels) will be shifted down by the smallest value (< 0)
		# Typically, only y coordinates can be less than 0

		vowels_y_less_than_zero = []

		for i in vowels_xy :
			for j in i :
				
				# Goes outside of bounding box
				if j[1] < 0 :
					vowels_y_less_than_zero.append(j[1])

		if vowels_y_less_than_zero :
			shift_y_by = abs(min(vowels_y_less_than_zero)) # | - y |

		# No need to shift
		else :
			shift_y_by = 0

		# Adjusts xy of each alphabet

		if debug :
			print(f"----------\n\nOffsetting all alphabets by {offset_in_alphabets_xy[0], offset_in_alphabets_xy[1] + shift_y_by}\nOffsetting all vowels by {offset_in_vowels_xy[0], offset_in_vowels_xy[1] + shift_y_by}\n")

		for i, xy in enumerate(alphabets_xy) :
			alphabets_xy[i] = (xy[0] + offset_in_alphabets_xy[0], xy[1] + shift_y_by + offset_in_alphabets_xy[1])

			if debug :
				print(f"Alphabet     = {alphabets[i]}\nShifted x, y = {alphabets_xy[i]}\n")

		# Adjusts xy of each vowel
		for i, vowels_for_this_alphabet in enumerate(vowels_xy) :
			for j, xy in enumerate(vowels_for_this_alphabet) :
				vowels_xy[i][j] = (xy[0] + offset_in_vowels_xy[0], xy[1] + shift_y_by + offset_in_vowels_xy[1])

				if debug :
					print(f"Vowel        = {vowels[i][j]} (for alphabet = {alphabets[i]})\nShifted x, y = {vowels_xy[i][j]}\n")

		# Calculates the total width that the image should take
		word_img_w = sum([alphabets_unique_wh[i][0] for i in alphabets])

		# Calculates the total height that the image should take
		word_img_h = 0

		for i, vowels_for_this_alphabet in enumerate(vowels) :

			# Calculates the height of vowels and alphabet together
			# ... = A_Height + A_Top + sum(V_Height) + sum(Y_gaps)
			this_alphabet_and_vowels_h = alphabets_unique_wh[alphabets[i]][1] + alphabets_unique_wh[alphabets[i]][3] + sum([vowels_unique_img[v].size[1] for v in vowels_for_this_alphabet]) + (len(vowels_for_this_alphabet) * alphabet_vowel_gap_y)

			if this_alphabet_and_vowels_h > word_img_h :
				word_img_h = this_alphabet_and_vowels_h

		if debug :
			print(f"----------\n\nCreating image of word\nWidth, Height = {word_img_w, word_img_h}")

		# Creates image
		word_img = Image.new("RGBA", (word_img_w, word_img_h), RGBA_BACKGROUND)
		draw_img = ImageDraw.Draw(word_img)

		# Draws alphabets
		draw_img.text(
			xy   = alphabets_xy[0],
			text = "".join(i for i in alphabets),
			font = self.font,
			fill = RGBA_TEXT
			)

		# Pastes vowels
		for i, vowels_for_this_alphabet in enumerate(vowels) :
			for j, v in enumerate(vowels_for_this_alphabet)  :
				word_img.paste(vowels_unique_img[v], vowels_xy[i][j], mask = vowels_unique_img[v])

		self.word_img = word_img

		# Also returns PIL Image object
		return word_img

if __name__ == "__main__" :

	# These are prerequisites before using the class and its methods

	# Connects alphabets to each other correctly (shapes alphabets)
	import arabic_reshaper

	arabic_reshaper_config = {
		"delete_harakat"         : False,
		"shift_harakat_position" : False,
		"delete_tatweel"         : True
	}

	reshaper = arabic_reshaper.ArabicReshaper(configuration = arabic_reshaper_config)

	# Right to Left orientation
	from bidi.algorithm import get_display

	# PIL font parameters
	font_path = ".\\Assets\\Font\\Amiri-Regular.ttf"
	font_size = 64

	# Correctly shapes text
	text_unshaped     = u"لَكِنَّ لَا بَدَّ أَنَّ أوْضَحَ لَكَ أَنَّ كُلُّ هَذِهِ الْأَفْكَارِ الْمَغْلُوطَةِ حَوْلَ اِسْتِنْكَارِ النَّشْوَةٌ وَتَمْجيدِ الْألَمِ نَشَّأَتٍ بِالْفِعْلِ، وَسَأَعْرُضُ لَكَ التَّفَاصِيلُ لِتَكْتَشِفٌ حَقِيقَةٌ وَأَسَاسٍ تِلْكَ السَّعَادَةً الْبَشَرِيَّةِ، فَلَا أحَدٌ يَرْفُضُ أَوْ يَكْرَهُ أَوْ يَتَجَنَّبُ الشُّعُورٌ بِالسَّعَادَةِ، وَلَكِنَّ بِفَضْلِ هَؤُلَاءِ الْأَشْخَاصِ الَّذِينَ لَا يُدْرِكُونَ بِأَنَّ السَّعَادَةً لَا بَدَّ أَنَّ نَسْتَشْعِرُهَا بِصُورَةِ أَكْثَرِ عَقْلَانِيَّةٍ وَمِنْطَقِيَّةٍ فَيَعْرُضُهُمْ هَذَا لِمُوَاجَهَةُ الظُّروفآ الْألِيمَةِ، وَأُكَرِّرُ بِأَنَّهُ لَا يُوجَدُ مَنْ يَرْغَبُ فِي الْحُبِّ وَنَيْلِ الْمَنَالِ وَيَتَلَذَّذُ بِالْآلَاَمِ، الْألَمَ هُوَ الْألَمُ وَلَكِنَّ نَتِيجَةً لِظُروفٍ مَا قَدْ تَكْمُنُ السعاده فِيمَا نَتَحَمَّلُهُ مِنْ كَدٍّ وَأُسِّيٍّ."
	text_shaped       = get_display(reshaper.reshape(text_unshaped), base_dir = "R")
	text_shaped_words = text_shaped.split(" ")

	# How to use the class and its methods

	# Inits object
	arabic_word = ArabicWord(
		word_string = text_shaped_words[0],
		font_path   = font_path,
		font_size   = font_size
		)

	# Creates image of word

	# When debug = True
	# The first "----------" output in terminal is because this method is being called here
	# And this method calls other methods and so on...

	# Just saying in case it looks out of place

	returned_word_img_through_method = arabic_word.create_img_of_word(offset_in_vowels_xy = (int(-0.1 * font_size), 0), debug = TERMINAL_LOGS)
	
	# word_img is a PIL Image object
	# It is also an attribute of the ArabicWord object
	# The method create_img_of_word(...) also returns the PIL Image object (same as attribute)

	# So the image can be displayed in 2 ways

	# Method 1 :
	arabic_word.word_img.show()	

	# Method 2 :
	returned_word_img_through_method.show()